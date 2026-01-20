"""Conversation context storage and persistence."""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.config import Config


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "user", "assistant", or "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    react_steps: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "react_steps": self.react_steps,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            react_steps=data.get("react_steps", []),
        )


@dataclass
class Output:
    """A saved output from the agent."""

    task: str
    result: str
    timestamp: str
    file_path: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task": self.task,
            "result": self.result,
            "timestamp": self.timestamp,
            "file_path": self.file_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Output":
        """Create from dictionary."""
        return cls(
            task=data["task"],
            result=data["result"],
            timestamp=data["timestamp"],
            file_path=data["file_path"],
        )


class ConversationContext:
    """Manages conversation context and persistence."""

    def __init__(self, session_id: str) -> None:
        """Initialize conversation context.

        Args:
            session_id: Unique session identifier.
        """
        self.session_id = session_id
        self.session_dir = Config.SESSIONS_DIR / session_id
        self.files_dir = self.session_dir / "files"
        self.outputs_dir = self.session_dir / "outputs"

        # Context state
        self.message_history: List[Message] = []
        self.created_files: Set[str] = set()
        self.protected_files: Set[str] = set()
        self.outputs: List[Output] = []
        self.metadata: Dict[str, Any] = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure all session directories exist."""
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    # --- Message Management ---

    def add_user_message(self, content: str) -> None:
        """Add a user message to history."""
        msg = Message(role="user", content=content)
        self.message_history.append(msg)
        self._append_to_history_log(msg)
        if Config.CONTEXT_AUTOSAVE:
            self.save()

    def add_assistant_message(
        self, content: str, react_steps: Optional[List[Dict[str, str]]] = None
    ) -> None:
        """Add an assistant message to history."""
        msg = Message(role="assistant", content=content, react_steps=react_steps or [])
        self.message_history.append(msg)
        self._append_to_history_log(msg)
        if Config.CONTEXT_AUTOSAVE:
            self.save()

    def get_message_history(self) -> List[Dict[str, str]]:
        """Get message history in LLM format."""
        return [{"role": msg.role, "content": msg.content} for msg in self.message_history]

    def get_recent_messages(self, count: int = 10) -> List[Dict[str, str]]:
        """Get recent messages."""
        return self.get_message_history()[-count:]

    # --- File Management ---

    def register_file(self, file_path: str, auto_protect: bool = True) -> None:
        """Register a created file.

        Args:
            file_path: Path to the file (relative to workspace).
            auto_protect: Whether to auto-protect the file.
        """
        self.created_files.add(file_path)
        if auto_protect:
            self.protected_files.add(file_path)
        self._update_protected_file()
        if Config.CONTEXT_AUTOSAVE:
            self.save()

    def protect_file(self, file_path: str) -> None:
        """Mark a file as protected."""
        self.protected_files.add(file_path)
        self._update_protected_file()

    def unprotect_file(self, file_path: str) -> None:
        """Remove protection from a file."""
        self.protected_files.discard(file_path)
        self._update_protected_file()

    def is_protected(self, file_path: str) -> bool:
        """Check if a file is protected."""
        return file_path in self.protected_files

    def get_created_files(self) -> List[str]:
        """Get list of created files."""
        return list(self.created_files)

    def get_protected_files(self) -> List[str]:
        """Get list of protected files."""
        return list(self.protected_files)

    def _update_protected_file(self) -> None:
        """Update .protected file."""
        protected_path = self.session_dir / ".protected"
        protected_path.write_text("\n".join(sorted(self.protected_files)))

    # --- Output Management ---

    def save_output(self, task: str, result: str) -> str:
        """Save an output and return the file path.

        Args:
            task: The task that produced this output.
            result: The output content.

        Returns:
            Path to the saved output file.
        """
        timestamp = datetime.utcnow()
        filename = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        file_path = self.outputs_dir / filename

        output_data = {
            "task": task,
            "result": result,
            "timestamp": timestamp.isoformat(),
        }
        file_path.write_text(json.dumps(output_data, indent=2))

        output = Output(
            task=task,
            result=result,
            timestamp=timestamp.isoformat(),
            file_path=str(file_path.relative_to(self.session_dir)),
        )
        self.outputs.append(output)

        if Config.CONTEXT_AUTOSAVE:
            self.save()

        return str(file_path)

    def get_outputs(self) -> List[Output]:
        """Get list of saved outputs."""
        return self.outputs

    # --- Persistence ---

    def save(self) -> None:
        """Save full context to disk."""
        self.metadata["updated_at"] = datetime.utcnow().isoformat()

        # Save context.json (full state)
        context_data = {
            "session_id": self.session_id,
            "metadata": self.metadata,
            "message_history": [msg.to_dict() for msg in self.message_history],
            "created_files": list(self.created_files),
            "protected_files": list(self.protected_files),
            "outputs": [out.to_dict() for out in self.outputs],
        }
        context_path = self.session_dir / "context.json"
        context_path.write_text(json.dumps(context_data, indent=2))

        # Save state.json (quick snapshot)
        state_data = {
            "session_id": self.session_id,
            "message_count": len(self.message_history),
            "created_files": list(self.created_files),
            "protected_files": list(self.protected_files),
            "output_count": len(self.outputs),
            "updated_at": self.metadata["updated_at"],
        }
        state_path = self.session_dir / "state.json"
        state_path.write_text(json.dumps(state_data, indent=2))

        # Save metadata.json
        metadata_path = self.session_dir / "metadata.json"
        metadata_path.write_text(json.dumps(self.metadata, indent=2))

    def _append_to_history_log(self, message: Message) -> None:
        """Append a message to history.jsonl."""
        history_path = self.session_dir / "history.jsonl"
        with open(history_path, "a") as f:
            f.write(json.dumps(message.to_dict()) + "\n")

    @classmethod
    def load(cls, session_id: str) -> "ConversationContext":
        """Load context from disk.

        Args:
            session_id: Session ID to load.

        Returns:
            Loaded ConversationContext.

        Raises:
            FileNotFoundError: If session does not exist.
        """
        session_dir = Config.SESSIONS_DIR / session_id
        context_path = session_dir / "context.json"

        if not context_path.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        data = json.loads(context_path.read_text())

        ctx = cls(session_id)
        ctx.metadata = data.get("metadata", ctx.metadata)
        ctx.message_history = [
            Message.from_dict(msg) for msg in data.get("message_history", [])
        ]
        ctx.created_files = set(data.get("created_files", []))
        ctx.protected_files = set(data.get("protected_files", []))
        ctx.outputs = [Output.from_dict(out) for out in data.get("outputs", [])]

        return ctx

    @classmethod
    def exists(cls, session_id: str) -> bool:
        """Check if a session exists."""
        context_path = Config.SESSIONS_DIR / session_id / "context.json"
        return context_path.exists()
