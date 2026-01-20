"""Output saving tool for persisting agent outputs."""
from typing import TYPE_CHECKING, Any, Dict, Optional

from src.tools.base import Tool

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext
    from src.session.conversation_context import ConversationContext


class SaveOutputTool(Tool):
    """Save important outputs for later retrieval."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize save output tool."""
        super().__init__(execution_context, conversation_context)
        if not conversation_context:
            raise ValueError("SaveOutputTool requires ConversationContext")

    @property
    def name(self) -> str:
        return "save_output"

    @property
    def description(self) -> str:
        return (
            "Save an important output or result for later retrieval. "
            "Use this to persist results that the user might need later."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Brief description of what this output is for",
                },
                "content": {
                    "type": "string",
                    "description": "The output content to save",
                },
            },
            "required": ["task_description", "content"],
        }

    async def execute(self, task_description: str, content: str) -> str:
        """Save output to persistent storage."""
        try:
            if not self.conversation_context:
                return "Error: No conversation context available"

            file_path = self.conversation_context.save_output(task_description, content)
            return f"Output saved successfully.\nTask: {task_description}\nSaved to: {file_path}"
        except Exception as exc:
            return f"Error saving output: {exc}"


class ListOutputsTool(Tool):
    """List all saved outputs in the session."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize list outputs tool."""
        super().__init__(execution_context, conversation_context)
        if not conversation_context:
            raise ValueError("ListOutputsTool requires ConversationContext")

    @property
    def name(self) -> str:
        return "list_outputs"

    @property
    def description(self) -> str:
        return "List all saved outputs from the current session."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self) -> str:
        """List all saved outputs."""
        try:
            if not self.conversation_context:
                return "Error: No conversation context available"

            outputs = self.conversation_context.get_outputs()
            if not outputs:
                return "No outputs saved in this session."

            lines = ["Saved outputs:"]
            for i, output in enumerate(outputs, 1):
                lines.append(f"\n{i}. {output.task}")
                lines.append(f"   Timestamp: {output.timestamp}")
                lines.append(f"   File: {output.file_path}")

            return "\n".join(lines)
        except Exception as exc:
            return f"Error listing outputs: {exc}"
