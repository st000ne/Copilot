from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

def utcnow():
    # Always use timezone-aware UTC timestamps
    return datetime.now(timezone.utc)

class ChatSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="New Chat")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    request_count: int = Field(default=0)
    messages: list["ChatMessage"] = Relationship(back_populates="session")

class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id")
    role: str
    content: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    session: Optional[ChatSession] = Relationship(back_populates="messages")
