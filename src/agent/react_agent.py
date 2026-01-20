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
        tool_descriptions = []
        for tool in tools:
            func = tool['function']
            name = func['name']
            desc = func['description']
            params = func.get('parameters', {}).get('properties', {})
            param_str = ", ".join([f'"{k}": <{v.get("type", "string")}>' for k, v in params.items()])
            tool_descriptions.append(f"- {name}: {desc}\n  Params: {{{param_str}}}")
        
        tool_lines = "\n".join(tool_descriptions)
        
        return f"""You are an AI agent with Python/Docker environment.

TOOLS:
{tool_lines}

FORMAT (strict):
Thought: <brief reasoning>
Action: tool_name({{"param": "value"}})

End with:
Action: Final Answer: <summary with file paths>

CRITICAL RULES:
1. ONE action per response. Wait for Observation.
2. USE YOUR KNOWLEDGE directly for content (articles, reports, data). DON'T search unless you truly need current info.
3. For documents/articles: Write content directly with write_file. You know enough!
4. For charts: Write a Python script with matplotlib, then execute it.
5. For PDFs: Use reportlab (pip install reportlab first).
6. NEVER repeat the same action twice.
7. Be EFFICIENT - minimize iterations.

DOCUMENT STRATEGY (3+ pages):
1. Write intro section -> write_file("sections/01_intro.md", content)
2. Write each section similarly (02, 03...)
3. Create Python script to combine sections + generate charts
4. Generate final PDF

CHARTS EXAMPLE (matplotlib):
```python
import matplotlib.pyplot as plt
data = {{"2025": 50, "2026": 75}}
plt.bar(data.keys(), data.values())
plt.savefig("chart.png")
```

Remember: You have extensive knowledge. Create content directly!"""

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
        
        # Loop detection: track recent actions to detect repetition
        recent_actions: List[str] = []
        max_repeated_actions = 2  # Stop if same action repeated more than 2 times

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
                action_payload = json.dumps(tool_params or {}, ensure_ascii=False)
                current_action = f"{action_type}:{action_payload}"
                
                # Check for repeated actions (loop detection)
                repeat_count = recent_actions.count(current_action)
                if repeat_count >= max_repeated_actions:
                    loop_msg = (
                        f"LOOP DETECTED: You have repeated the same action '{action_type}' {repeat_count + 1} times. "
                        f"The task appears to be complete. Please provide a Final Answer summarizing what was done, "
                        f"or try a COMPLETELY DIFFERENT approach if the task is not complete."
                    )
                    messages.append({"role": "user", "content": f"Observation: {loop_msg}"})
                    react_steps.append({"type": "error", "content": loop_msg})
                    
                    # Force stop after too many repeats
                    if repeat_count >= max_repeated_actions + 1:
                        state.set_final_answer(f"Task stopped due to repeated actions. Last action: {action_type}")
                        react_steps.append({"type": "final_answer", "content": state.final_answer})
                        break
                    continue
                
                # Track this action
                recent_actions.append(current_action)
                # Keep only last 10 actions
                if len(recent_actions) > 10:
                    recent_actions.pop(0)
                
                try:
                    tool = self.tools.get_tool(action_type)
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
