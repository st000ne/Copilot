from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from backend.db import init_db, get_session
from backend.models import ChatSession, ChatMessage
import asyncio
from backend.pipeline import run_chat

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

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 500
    session_id: Optional[int] = None

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
        return {"session_id": session_id, "messages": messages}


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    with get_session() as db:
        session = db.get(ChatSession, req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Simple rate limit
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
        recent_msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == req.session_id)
            .filter(ChatMessage.created_at >= cutoff)
            .count()
        )
        if recent_msgs >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded (20 requests/minute).")

        total_chars = sum(len(m.content) for m in req.messages)
        if total_chars > 20000:
            raise HTTPException(status_code=400, detail="Input too long (20k char limit).")

        # Save user messages
        for m in req.messages:
            db.add(ChatMessage(session_id=req.session_id, role=m.role, content=m.content))
        db.commit()

        try:
            # Run synchronous pipeline safely in background thread
            loop = asyncio.get_running_loop()
            reply = await loop.run_in_executor(None, lambda: run_chat([m.model_dump() for m in req.messages]))

            # Save assistant message
            db.add(ChatMessage(session_id=req.session_id, role=reply["role"], content=reply["content"]))
            session.request_count += 1
            db.commit()

            return {"reply": reply, "session_id": req.session_id}

        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Pipeline error: {str(e)}")
