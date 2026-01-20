"""ReAct Agent with session and context support."""
import json
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from src.agent.state import AgentState
from src.config import Config
from src.models.llm_client import LLMClient
from src.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from src.session.conversation_context import ConversationContext


class ReActAgent:
    """ReAct (Reasoning + Acting) Agent implementation."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize ReAct agent.

        Args:
            tool_registry: Registry of available tools.
            conversation_context: Optional conversation context for persistence.
        """
        self.llm = LLMClient()
        self.tools = tool_registry
        self.max_iterations = Config.MAX_ITERATIONS
        self.conversation_context = conversation_context

    def _build_system_prompt(self) -> str:
        """Build the system prompt for ReAct reasoning."""
        tools = self.tools.get_tools_schema()
        tool_lines = "\n".join(
            [f"- {tool['function']['name']}: {tool['function']['description']}" for tool in tools]
        )
        return (
            "You are a helpful AI assistant that uses the ReAct framework.\n\n"
            "IMPORTANT: For complex tasks (tasks requiring multiple steps, file creation, "
            "code execution, or any non-trivial work), you MUST first create a detailed plan "
            "in your Thought. Break down the task into clear, sequential steps. "
            "Then execute each step using tools.\n\n"
            "Available tools:\n"
            f"{tool_lines}\n\n"
            "Follow this format strictly:\n"
            "Thought: <your reasoning - for complex tasks, create a detailed plan here>\n"
            "Action: <tool_name>({\"param\": \"value\"})\n"
            "Observation: <result>\n"
            "...\n"
            "When done, respond with:\n"
            "Action: Final Answer: <your final answer>\n\n"
            "RULES:\n"
            "1. Always think before acting\n"
            "2. For complex tasks, create a plan first\n"
            "3. Execute one action at a time\n"
            "4. Use tools to accomplish tasks - don't just describe what you would do\n"
            "5. Save important outputs using save_output tool\n"
        )

    def _parse_action(
        self, response: str
    ) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
        """Parse action from LLM response."""
        action_match = re.search(r"Action:\s*(.+)", response, re.IGNORECASE)
        if not action_match:
            return None, None, None

        action_text = action_match.group(1).strip()
        if action_text.lower().startswith("final answer:"):
            return "final_answer", action_text[len("final answer:") :].strip(), None
        if "Final Answer:" in action_text:
            return "final_answer", action_text.split("Final Answer:", 1)[1].strip(), None

        # Match tool call: tool_name({"param": "value"})
        tool_match = re.match(r"(\w+)\((.*)\)", action_text, re.DOTALL)
        if tool_match:
            tool_name = tool_match.group(1)
            params_text = tool_match.group(2).strip()
            try:
                params = json.loads(params_text) if params_text else {}
            except json.JSONDecodeError:
                params = {}
            return tool_name, None, params

        return None, None, None

    def _get_conversation_history_messages(self) -> List[Dict[str, str]]:
        """Get previous conversation messages for context."""
        if not self.conversation_context:
            return []
        
        # Get recent messages to provide context
        history = self.conversation_context.get_recent_messages(count=10)
        return history

    async def run(self, task: str) -> AgentState:
        """Run the ReAct loop for a given task.

        Args:
            task: The task to execute.

        Returns:
            AgentState with the results.
        """
        state = AgentState(task=task)

        # Build initial messages with conversation history for context
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
        ]

        # Add recent conversation history for context
        history = self._get_conversation_history_messages()
        if history:
            messages.append({
                "role": "system",
                "content": "Previous conversation context:\n" + "\n".join(
                    [f"{m['role']}: {m['content'][:200]}..." if len(m['content']) > 200 else f"{m['role']}: {m['content']}"
                     for m in history[-5:]]  # Last 5 messages
                )
            })

        messages.append({"role": "user", "content": f"Task: {task}"})

        tool_names = {tool.name for tool in self.tools.get_all_tools()}
        react_steps = []

        while state.iteration < self.max_iterations and not state.is_complete:
            state.iteration += 1
            response = await self.llm.chat_completion(messages)

            # Extract thought
            thought_match = re.search(
                r"Thought:\s*(.+?)(?=Action:|$)", response, re.DOTALL | re.IGNORECASE
            )
            if thought_match:
                thought = thought_match.group(1).strip()
                state.add_thought(thought)
                messages.append({"role": "assistant", "content": f"Thought: {thought}"})
                react_steps.append({"type": "thought", "content": thought})

            # Parse and execute action
            action_type, final_answer, tool_params = self._parse_action(response)

            if action_type == "final_answer":
                state.set_final_answer(final_answer or "")
                messages.append(
                    {"role": "assistant", "content": f"Final Answer: {final_answer or ''}"}
                )
                react_steps.append({"type": "final_answer", "content": final_answer or ""})
                break

            if action_type in tool_names:
                try:
                    tool = self.tools.get_tool(action_type)
                    action_payload = json.dumps(tool_params or {}, ensure_ascii=False)
                    state.add_action(f"{action_type}({action_payload})")
                    messages.append(
                        {"role": "assistant", "content": f"Action: {action_type}({action_payload})"}
                    )
                    react_steps.append({"type": "action", "tool": action_type, "params": tool_params})

                    result = await tool.execute(**(tool_params or {}))
                    state.add_observation(result)
                    messages.append({"role": "user", "content": f"Observation: {result}"})
                    react_steps.append({"type": "observation", "content": result})
                except Exception as exc:
                    error_msg = f"Error executing {action_type}: {exc}"
                    state.add_observation(error_msg)
                    messages.append({"role": "user", "content": f"Observation: {error_msg}"})
                    react_steps.append({"type": "error", "content": error_msg})
                continue

            error_msg = (
                "Invalid action format. Use: "
                "Action: tool_name({\"param\": \"value\"}) or Action: Final Answer: <answer>"
            )
            state.add_observation(error_msg)
            messages.append({"role": "user", "content": f"Observation: {error_msg}"})

        if not state.is_complete and state.iteration >= self.max_iterations:
            state.set_final_answer("Maximum iterations reached. Unable to complete the task.")

        # Save to conversation context if available
        if self.conversation_context:
            self.conversation_context.add_user_message(task)
            self.conversation_context.add_assistant_message(
                state.final_answer, react_steps=react_steps
            )

        return state
