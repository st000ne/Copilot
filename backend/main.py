from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import func
import os
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from backend.db import init_db, get_session
from backend.models import ChatSession, ChatMessage
import asyncio
from backend.pipeline import run_chat, _extract_texts_from_faiss_index
from backend.memory import (
    add_memory,
    get_or_create_faiss_index,
    delete_memory,
    edit_memory
)
from backend.docs import (
    list_documents,
    add_document,
    delete_document_by_filename,
    edit_document
)
from backend.file_utils import extract_text_from_file
from backend.docs import reindex_docs
from backend.memory import reindex_memories


load_dotenv()

app = FastAPI(title="AI Copilot Prototype API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

RATE_LIMIT = 20
WINDOW_MINUTES = 1
UPLOADS_DIR = "backend/data/docs"

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 500
    session_id: Optional[int] = None

class TextPayload(BaseModel):
    text: str

class EditPayload(BaseModel):
    old_text: str
    new_text: str

class DeleteDocPayload(BaseModel):
    filename: str

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/session")
def new_session():
    with get_session() as db:
        s = ChatSession()
        db.add(s)
        db.commit()
        db.refresh(s)
        return {"session_id": s.id, "created_at": s.created_at}


@app.get("/sessions")
def list_sessions():
    """List all chat sessions (id, title, created_at, updated_at, request_count)."""
    with get_session() as db:
        sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
        return sessions


@app.patch("/session/{session_id}")
def rename_session(session_id: int, data: dict = Body(...)):
    """Rename a chat session."""
    new_name = data.get("name")
    if not new_name:
        raise HTTPException(status_code=400, detail="Missing 'title'")
    with get_session() as db:
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session.name = new_name
        db.commit()
        db.refresh(session)
        return session


@app.delete("/session/{session_id}")
def delete_session(session_id: int):
    """Delete a session and its messages."""
    with get_session() as db:
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        # Delete all messages first
        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
        db.delete(session)
        db.commit()
        return {"ok": True, "deleted_session_id": session_id}


@app.get("/session/{session_id}/history")
def get_history(session_id: int):
    with get_session() as db:
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        return {
            "session_id": session_id,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                    "updated_at": m.updated_at.isoformat(),
                }
                for m in messages
            ],
        }


@app.patch("/message/{message_id}/edit")
async def edit_and_regenerate(message_id: int, content: str):
    with get_session() as db:
        msg = db.get(ChatMessage, message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")

        session = db.get(ChatSession, msg.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        msg.content = content
        msg.updated_at = datetime.now(timezone.utc)

        # Remove later assistant messages (after this user message)
        later_msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == msg.session_id)
            .filter(ChatMessage.id > message_id)
            .filter(ChatMessage.role == "assistant")
            .all()
        )
        for lm in later_msgs:
            db.delete(lm)
        db.commit()

        # Re-run the chat pipeline
        all_msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == msg.session_id)
            .order_by(ChatMessage.id)
            .all()
        )

        loop = asyncio.get_running_loop()
        reply = await loop.run_in_executor(None, lambda: run_chat([m.model_dump() for m in all_msgs]))

        # Save the new assistant reply
        new_msg = ChatMessage(
            session_id=msg.session_id, role=reply["role"], content=reply["content"]
        )
        db.add(new_msg)
        session.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "reply": {"id": new_msg.id, "content": new_msg.content, "role": new_msg.role},
            "edited_message_id": message_id,
        }


@app.post("/session/{session_id}/continue")
async def continue_chat(session_id: int):
    with get_session() as db:
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id)
            .all()
        )

        loop = asyncio.get_running_loop()
        reply = await loop.run_in_executor(None, lambda: run_chat([m.model_dump() for m in messages]))

        new_msg = ChatMessage(session_id=session_id, role="assistant", content=reply["content"])
        db.add(new_msg)
        db.commit()

        return {"id": new_msg.id, "content": new_msg.content, "role": "assistant"}


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    with get_session() as db:
        session = db.get(ChatSession, req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 🔹 Rate limiting
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
        recent_msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == req.session_id)
            .filter(ChatMessage.created_at >= cutoff)
            .count()
        )
        if recent_msgs >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded (20 requests/minute).")

        # 🔹 Validate input length
        total_chars = sum(len(m.content) for m in req.messages)
        if total_chars > 20000:
            raise HTTPException(status_code=400, detail="Input too long (20k char limit).")

        # 🔹 Save user messages and collect them for response
        user_messages = []
        for m in req.messages:
            msg = ChatMessage(session_id=req.session_id, role=m.role, content=m.content)
            db.add(msg)
            db.flush()  # ensures ID is generated before commit
            user_messages.append(msg)
        db.commit()

        # 🔹 Update session activity timestamp
        session.updated_at = datetime.now(timezone.utc)
        db.add(session)
        db.commit()

        try:
            # 🔹 Run synchronous pipeline safely in background thread
            loop = asyncio.get_running_loop()
            reply = await run_chat([m.model_dump() for m in req.messages])

            # 🔹 Save assistant reply
            assistant_msg = ChatMessage(
                session_id=req.session_id, role=reply["role"], content=reply["content"]
            )
            db.add(assistant_msg)
            db.flush()
            session.request_count += 1
            db.commit()

            # 🔹 Return all messages (user + assistant) with IDs
            return {
                "session_id": req.session_id,
                "messages": [
                    {
                        "id": m.id,
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in user_messages + [assistant_msg]
                ],
            }

        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Pipeline error: {str(e)}")


# ===== MEMORY MANAGEMENT =====
@app.get("/memory/list")
def list_memories():
    """List all memory items stored in FAISS."""
    try:
        index = get_or_create_faiss_index()
        texts = _extract_texts_from_faiss_index(index)
        return {"facts": texts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing memories: {e}")


@app.post("/memory/add")
def add_memory_endpoint(payload: TextPayload):
    """Add a memory (fact) to FAISS index."""
    try:
        add_memory(payload.text)
        return {"ok": True, "text": payload.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add memory: {e}")


@app.patch("/memory/edit")
def edit_memory_endpoint(payload: EditPayload):
    try:
        return edit_memory(payload.old_text, payload.new_text)
    except Exception as e:
        return JSONResponse(status_code=500, content={"edited": False, "reason": str(e)})


@app.delete("/memory/delete")
def delete_memory_endpoint(payload: TextPayload):
    try:
        return delete_memory(payload.text)
    except Exception as e:
        return JSONResponse(status_code=500, content={"deleted": False, "reason": str(e)})


# ===== DOCS MANAGEMENT =====
@app.get("/docs/list")
def list_docs():
    """List all document chunks from FAISS."""
    try:
        return {"docs": list_documents() or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing docs: {e}")


@app.post("/docs/add")
def add_docs_endpoint(payload: TextPayload):
    try:
        n_chunks = add_document(payload.text)
        return {"ok": True, "chunks_added": n_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add doc: {e}")


@app.patch("/docs/edit")
def edit_doc_endpoint(payload: EditPayload):
    try:
        result = edit_document(payload.old_text, payload.new_text)
        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to edit doc: {e}")


@app.delete("/docs/delete")
def delete_doc_endpoint(payload: DeleteDocPayload):
    try:
        result = delete_document_by_filename(payload.filename)
        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete doc: {e}")


@app.post("/docs/upload")
async def upload_docs(file: UploadFile = File(...)):
    """Upload one or more files, extract text, and index them into FAISS."""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    results = []

    file_path = os.path.join(UPLOADS_DIR, file.filename)
    try:
        # Save raw file
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Extract text
        text = extract_text_from_file(file_path)
        if not text.strip():
            results.append({"file": file.filename, "ok": False, "reason": "No text extracted"})

        # Add to FAISS
        add_result = add_document(text, base_name=os.path.splitext(file.filename)[0])

        results.append({
            "file": file.filename,
            "ok": True,
            "chunks_added": add_result["added"],
            "total_chunks": add_result["chunks"],
        })

    except Exception as e:
        results.append({"file": file.filename, "ok": False, "error": str(e)})

    return {"results": results}


@app.post("/docs/reindex")
async def rebuild_docs_index():
    result = reindex_docs()
    return result

@app.post("/memories/reindex")
async def rebuild_memories_index():
    result = reindex_memories()
    return result
