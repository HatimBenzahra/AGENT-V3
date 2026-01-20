"""Terminal command execution tool."""
from typing import TYPE_CHECKING, Any, Dict, Optional

from src.tools.base import Tool

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext
    from src.session.conversation_context import ConversationContext


class TerminalTool(Tool):
    """Execute shell commands in the Docker workspace."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize terminal tool.

        Args:
            execution_context: Required Docker execution context.
            conversation_context: Optional conversation context.
        """
        super().__init__(execution_context, conversation_context)
        if not execution_context:
            raise ValueError("TerminalTool requires DockerExecutionContext")

    @property
    def name(self) -> str:
        return "execute_command"

    @property
    def description(self) -> str:
        return (
            "Execute shell commands in the workspace. "
            "Use this to run any terminal command like 'ls', 'python script.py', "
            "'pip install package', 'git clone', etc. "
            "Commands run in an isolated Docker container with Python 3.11."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute (e.g., 'ls -la', 'python script.py', 'pip install requests')",
                },
            },
            "required": ["command"],
        }

    @property
    def requires_docker(self) -> bool:
        return True

    async def execute(self, command: str) -> str:
        """Execute command in Docker container.

        Args:
            command: Shell command to execute.

        Returns:
            Command output with exit code.
        """
        if not self.execution_context:
            return "Error: No execution context available"

        stdout, stderr, exit_code = await self.execution_context.execute_command(command)

        result_parts = [f"Exit code: {exit_code}"]

        if stdout:
            result_parts.append(f"Output:\n{stdout}")
        if stderr:
            result_parts.append(f"Errors:\n{stderr}")

        if not stdout and not stderr and exit_code == 0:
            result_parts.append("Command completed successfully (no output)")

        return "\n".join(result_parts)
