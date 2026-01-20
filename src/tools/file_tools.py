"""File operation tools (read, write, list, delete)."""
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from src.tools.base import Tool

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext
    from src.session.conversation_context import ConversationContext


class ReadFileTool(Tool):
    """Read file contents from workspace."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize read file tool."""
        super().__init__(execution_context, conversation_context)
        if not execution_context:
            raise ValueError("ReadFileTool requires DockerExecutionContext")

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file from the workspace."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file relative to workspace (e.g., 'script.py', 'data/file.txt')",
                },
            },
            "required": ["file_path"],
        }

    @property
    def requires_docker(self) -> bool:
        return True

    async def execute(self, file_path: str) -> str:
        """Read file contents."""
        try:
            path = self.execution_context.resolve_path(file_path)
            if not path.exists():
                return f"Error: File not found: {file_path}"
            if not path.is_file():
                return f"Error: Path is not a file: {file_path}"

            content = path.read_text(encoding="utf-8")
            lines = content.count("\n") + 1
            return f"File: {file_path} ({lines} lines)\n\n{content}"
        except Exception as exc:
            return f"Error reading file: {exc}"


class WriteFileTool(Tool):
    """Write content to a file in workspace."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize write file tool."""
        super().__init__(execution_context, conversation_context)
        if not execution_context:
            raise ValueError("WriteFileTool requires DockerExecutionContext")

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return (
            "Write content to a file in the workspace. "
            "Creates the file if it doesn't exist. Creates parent directories if needed."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file relative to workspace (e.g., 'script.py', 'src/utils.py')",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    @property
    def requires_docker(self) -> bool:
        return True

    async def execute(self, file_path: str, content: str) -> str:
        """Write file contents."""
        try:
            path = self.execution_context.resolve_path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

            # Register file in context if available
            if self.conversation_context:
                self.conversation_context.register_file(file_path, auto_protect=True)

            return f"File written successfully: {file_path}\nSize: {len(content)} bytes ({content.count(chr(10)) + 1} lines)"
        except Exception as exc:
            return f"Error writing file: {exc}"


class ListDirectoryTool(Tool):
    """List directory contents."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize list directory tool."""
        super().__init__(execution_context, conversation_context)
        if not execution_context:
            raise ValueError("ListDirectoryTool requires DockerExecutionContext")

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and directories in the workspace."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Directory path relative to workspace (default: '.' for root)",
                    "default": ".",
                },
            },
            "required": [],
        }

    @property
    def requires_docker(self) -> bool:
        return True

    async def execute(self, directory_path: str = ".") -> str:
        """List directory contents."""
        try:
            path = self.execution_context.resolve_path(directory_path)
            if not path.exists():
                return f"Error: Directory not found: {directory_path}"
            if not path.is_dir():
                return f"Error: Path is not a directory: {directory_path}"

            items = []
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue  # Skip hidden files
                item_type = "DIR " if item.is_dir() else "FILE"
                if item.is_file():
                    size = item.stat().st_size
                    items.append(f"{item_type} {item.name:40} {size:>10} bytes")
                else:
                    items.append(f"{item_type} {item.name}/")

            if not items:
                return f"Directory '{directory_path}' is empty"

            return f"Directory: {directory_path}\n\n" + "\n".join(items)
        except Exception as exc:
            return f"Error listing directory: {exc}"


class DeleteFileTool(Tool):
    """Delete a file from workspace (with protection checks)."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize delete file tool."""
        super().__init__(execution_context, conversation_context)
        if not execution_context:
            raise ValueError("DeleteFileTool requires DockerExecutionContext")

    @property
    def name(self) -> str:
        return "delete_file"

    @property
    def description(self) -> str:
        return (
            "Delete a file from the workspace. "
            "WARNING: Protected files (user-requested) cannot be deleted. "
            "Use with caution."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file to delete relative to workspace",
                },
                "force": {
                    "type": "boolean",
                    "description": "Force delete even if protected (default: false)",
                    "default": False,
                },
            },
            "required": ["file_path"],
        }

    @property
    def requires_docker(self) -> bool:
        return True

    async def execute(self, file_path: str, force: bool = False) -> str:
        """Delete file with protection check."""
        try:
            # Check protection
            if self.conversation_context and not force:
                if self.conversation_context.is_protected(file_path):
                    return (
                        f"Error: File '{file_path}' is protected and cannot be deleted. "
                        "This file was created based on user request. "
                        "Use force=true to override (not recommended)."
                    )

            path = self.execution_context.resolve_path(file_path)
            if not path.exists():
                return f"Error: File not found: {file_path}"
            if not path.is_file():
                return f"Error: Path is not a file: {file_path}"

            path.unlink()

            # Update context if available
            if self.conversation_context:
                self.conversation_context.created_files.discard(file_path)
                self.conversation_context.protected_files.discard(file_path)
                self.conversation_context.save()

            return f"File deleted successfully: {file_path}"
        except Exception as exc:
            return f"Error deleting file: {exc}"
