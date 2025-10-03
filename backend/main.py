import os
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.pipeline import run_chat

load_dotenv()  # loads .env in dev

app = FastAPI(title="AI Copilot Prototype API")

# allow local dev from Vite default port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 500

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        reply = run_chat([m.model_dump() for m in req.messages])
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
