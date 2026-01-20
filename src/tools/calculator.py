"""Calculator tool for mathematical operations."""
import math
from typing import TYPE_CHECKING, Any, Dict, Optional

from src.tools.base import Tool

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext
    from src.session.conversation_context import ConversationContext


class CalculatorTool(Tool):
    """Tool for performing mathematical calculations."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize calculator tool."""
        super().__init__(execution_context, conversation_context)

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Performs mathematical calculations. Supports basic operators "
            "(+, -, *, /, **), and math functions like sqrt, sin, cos."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression to evaluate, e.g. '2 + 2' or 'sqrt(16)'",
                }
            },
            "required": ["expression"],
        }

    async def execute(self, expression: str) -> str:
        """Execute the calculation."""
        try:
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("__")
            }
            allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"Result: {result}"
        except Exception as exc:
            return f"Error evaluating expression: {exc}"
