"""Session management endpoints."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.session.session_manager import SessionManager, SessionInfo
from src.session.conversation_context import ConversationContext

router = APIRouter()
session_manager = SessionManager()


class SessionResponse(BaseModel):
    """Session information response."""
    session_id: str
    created_at: str
    updated_at: str
    message_count: int
    file_count: int


class SessionListResponse(BaseModel):
    """List of sessions response."""
    sessions: List[SessionResponse]


class MessageResponse(BaseModel):
    """Message in conversation."""
    role: str
    content: str
    timestamp: str


class SessionDetailResponse(BaseModel):
    """Detailed session information."""
    session_id: str
    created_at: str
    updated_at: str
    message_count: int
    file_count: int
    messages: List[MessageResponse]
    created_files: List[str]
    protected_files: List[str]


@router.get("", response_model=SessionListResponse)
async def list_sessions():
    """List all available sessions."""
    sessions = session_manager.list_sessions()
    return SessionListResponse(
        sessions=[
            SessionResponse(
                session_id=s.session_id,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=s.message_count,
                file_count=s.file_count,
            )
            for s in sessions
        ]
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str):
    """Get detailed session information."""
    if not session_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        context = ConversationContext.load(session_id)
        messages = [
            MessageResponse(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
            )
            for msg in context.message_history
        ]

        return SessionDetailResponse(
            session_id=session_id,
            created_at=context.metadata.get("created_at", ""),
            updated_at=context.metadata.get("updated_at", ""),
            message_count=len(context.message_history),
            file_count=len(context.created_files),
            messages=messages,
            created_files=list(context.created_files),
            protected_files=list(context.protected_files),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if not session_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")

    return {"message": f"Session {session_id} deleted"}


@router.post("/{session_id}/save")
async def save_session(session_id: str):
    """Force save a session."""
    if not session_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        context = ConversationContext.load(session_id)
        context.save()
        return {"message": f"Session {session_id} saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
