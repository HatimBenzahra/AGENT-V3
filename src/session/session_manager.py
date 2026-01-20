"""Session lifecycle management."""
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.config import Config
from src.execution.docker_context import DockerExecutionContext
from src.session.conversation_context import ConversationContext


@dataclass
class SessionInfo:
    """Information about a session."""

    session_id: str
    created_at: str
    updated_at: str
    message_count: int
    file_count: int


class SessionManager:
    """Manages session lifecycle."""

    def __init__(self) -> None:
        """Initialize session manager."""
        Config.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def create_session(self) -> str:
        """Create a new session.

        Returns:
            New session ID.
        """
        session_id = str(uuid.uuid4())[:8]
        # Create context to initialize directories
        ctx = ConversationContext(session_id)
        ctx.save()
        return session_id

    def list_sessions(self) -> List[SessionInfo]:
        """List all available sessions.

        Returns:
            List of SessionInfo objects.
        """
        sessions = []
        if not Config.SESSIONS_DIR.exists():
            return sessions

        for session_dir in Config.SESSIONS_DIR.iterdir():
            if not session_dir.is_dir():
                continue

            context_path = session_dir / "context.json"
            if not context_path.exists():
                continue

            try:
                import json
                data = json.loads(context_path.read_text())
                metadata = data.get("metadata", {})
                sessions.append(
                    SessionInfo(
                        session_id=session_dir.name,
                        created_at=metadata.get("created_at", "unknown"),
                        updated_at=metadata.get("updated_at", "unknown"),
                        message_count=len(data.get("message_history", [])),
                        file_count=len(data.get("created_files", [])),
                    )
                )
            except Exception:
                continue

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return ConversationContext.exists(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its workspace.

        Args:
            session_id: Session ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        session_dir = Config.SESSIONS_DIR / session_id
        if not session_dir.exists():
            return False

        import shutil
        shutil.rmtree(session_dir, ignore_errors=True)
        return True


class Session:
    """Represents an active session with context and execution environment."""

    def __init__(
        self,
        session_id: str,
        context: ConversationContext,
        docker_context: DockerExecutionContext,
    ) -> None:
        """Initialize session.

        Args:
            session_id: Session identifier.
            context: Conversation context.
            docker_context: Docker execution context.
        """
        self.session_id = session_id
        self.context = context
        self.docker_context = docker_context

    @classmethod
    async def create_new(cls) -> "Session":
        """Create a new session with fresh context and Docker environment.

        Returns:
            New Session instance.
        """
        session_id = str(uuid.uuid4())[:8]
        context = ConversationContext(session_id)
        docker_ctx = DockerExecutionContext(session_id)

        await docker_ctx.start()
        context.save()

        return cls(session_id, context, docker_ctx)

    @classmethod
    async def resume(cls, session_id: str) -> "Session":
        """Resume an existing session.

        Args:
            session_id: Session ID to resume.

        Returns:
            Resumed Session instance.

        Raises:
            FileNotFoundError: If session does not exist.
        """
        context = ConversationContext.load(session_id)
        docker_ctx = DockerExecutionContext(session_id)

        await docker_ctx.start()

        return cls(session_id, context, docker_ctx)

    async def close(self) -> None:
        """Close the session (save context and stop Docker)."""
        self.context.save()
        await self.docker_context.stop()

    async def cleanup(self) -> None:
        """Cleanup session (stop Docker, optionally delete workspace)."""
        self.context.save()
        await self.docker_context.cleanup()
