"""ReAct Agent with session and context support."""
import json
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from src.agent.state import AgentState
from src.agent.recovery import RecoveryManager, ErrorPatterns
from src.config import Config
from src.models.llm_client import LLMClient
from src.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from src.session.conversation_context import ConversationContext


class ReActAgent:

    def __init__(
        self,
        tool_registry: ToolRegistry,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        self.llm = LLMClient()
        self.tools = tool_registry
        self.max_iterations = Config.MAX_ITERATIONS
        self.conversation_context = conversation_context
        self.recovery_manager = RecoveryManager(max_retries=3)

    def _build_system_prompt(self) -> str:
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
        
        return f"""You are an autonomous AI agent. Execute tasks efficiently using the available tools.

AVAILABLE TOOLS:
{tool_lines}

RESPONSE FORMAT (strict - follow exactly):
Thought: <your reasoning - keep it brief>
Action: tool_name({{"param": "value"}})

When task is complete:
Action: Final Answer: <your response to the user>

RULES:
1. ONE action per response. Wait for the observation before continuing.
2. Be efficient - don't repeat failed actions, try alternatives.
3. For file operations, verify paths exist before writing.
4. For web searches, extract key information and cite sources.
5. When creating documents (PDF, LaTeX), verify compilation succeeds.
6. Keep Final Answer concise but include all relevant file paths.

IMPORTANT:
- Never invent data. Use web_search for facts.
- If a tool fails, diagnose and fix the issue.
- Always verify your work before declaring success.
"""

    def _parse_action(
        self, response: str
    ) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
        action_match = re.search(r"Action:\s*(.+)", response, re.IGNORECASE)
        if not action_match:
            return None, None, None

        action_text = action_match.group(1).strip()
        if action_text.lower().startswith("final answer:"):
            return "final_answer", action_text[len("final answer:") :].strip(), None
        if "Final Answer:" in action_text:
            return "final_answer", action_text.split("Final Answer:", 1)[1].strip(), None

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
        if not self.conversation_context:
            return []
        history = self.conversation_context.get_recent_messages(count=10)
        return history

    async def run(self, task: str) -> AgentState:
        state = AgentState(task=task)
        self.recovery_manager.reset()

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
        ]

        history = self._get_conversation_history_messages()
        if history:
            messages.append({
                "role": "system",
                "content": "Previous conversation context:\n" + "\n".join(
                    [f"{m['role']}: {m['content'][:200]}..." if len(m['content']) > 200 else f"{m['role']}: {m['content']}"
                     for m in history[-5:]]
                )
            })

        messages.append({"role": "user", "content": f"Task: {task}"})

        tool_names = {tool.name for tool in self.tools.get_all_tools()}
        react_steps = []
        
        recent_actions: List[str] = []
        max_repeated_actions = 2

        while state.iteration < self.max_iterations and not state.is_complete:
            state.iteration += 1
            response = await self.llm.chat_completion(messages)

            thought_match = re.search(
                r"Thought:\s*(.+?)(?=Action:|$)", response, re.DOTALL | re.IGNORECASE
            )
            if thought_match:
                thought = thought_match.group(1).strip()
                state.add_thought(thought)
                messages.append({"role": "assistant", "content": f"Thought: {thought}"})
                react_steps.append({"type": "thought", "content": thought})

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
                
                repeat_count = recent_actions.count(current_action)
                if repeat_count >= max_repeated_actions:
                    loop_msg = (
                        f"LOOP DETECTED: You have repeated '{action_type}' {repeat_count + 1} times. "
                        f"Provide a Final Answer or try a DIFFERENT approach."
                    )
                    messages.append({"role": "user", "content": f"Observation: {loop_msg}"})
                    react_steps.append({"type": "error", "content": loop_msg})
                    
                    if repeat_count >= max_repeated_actions + 1:
                        state.set_final_answer(f"Task stopped due to repeated actions. Last action: {action_type}")
                        react_steps.append({"type": "final_answer", "content": state.final_answer})
                        break
                    continue
                
                recent_actions.append(current_action)
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
                    
                    error_type, _ = ErrorPatterns.detect_error_type(result)
                    if error_type.value != "unknown" and "Error" in result:
                        recovery_action = self.recovery_manager.analyze_error(
                            error_message=result,
                            action=action_type,
                            params=tool_params,
                        )
                        
                        if recovery_action and recovery_action.action_type == "execute_command":
                            recovery_msg = f"[SELF-HEALING] Detected {error_type.value}. Trying: {recovery_action.description}"
                            messages.append({"role": "user", "content": f"Observation: {recovery_msg}"})
                            react_steps.append({"type": "recovery", "content": recovery_msg})
                            
                            recovery_tool = self.tools.get_tool("execute_command")
                            if recovery_tool:
                                recovery_result = await recovery_tool.execute(**recovery_action.params)
                                messages.append({"role": "user", "content": f"Recovery result: {recovery_result}"})
                                react_steps.append({"type": "observation", "content": f"Recovery: {recovery_result}"})
                                
                                retry_result = await tool.execute(**(tool_params or {}))
                                state.add_observation(retry_result)
                                messages.append({"role": "user", "content": f"Observation (retry): {retry_result}"})
                                react_steps.append({"type": "observation", "content": retry_result})
                                continue
                    
                    state.add_observation(result)
                    messages.append({"role": "user", "content": f"Observation: {result}"})
                    react_steps.append({"type": "observation", "content": result})
                        
                except Exception as exc:
                    error_msg = f"Error executing {action_type}: {exc}"
                    
                    recovery_action = self.recovery_manager.analyze_error(
                        error_message=str(exc),
                        action=action_type,
                        params=tool_params,
                    )
                    
                    if recovery_action and recovery_action.action_type == "execute_command":
                        recovery_msg = f"[SELF-HEALING] Error detected. Trying: {recovery_action.description}"
                        messages.append({"role": "user", "content": f"Observation: {error_msg}\n{recovery_msg}"})
                        react_steps.append({"type": "recovery", "content": recovery_msg})
                        
                        try:
                            recovery_tool = self.tools.get_tool("execute_command")
                            if recovery_tool:
                                recovery_result = await recovery_tool.execute(**recovery_action.params)
                                messages.append({"role": "user", "content": f"Recovery result: {recovery_result}"})
                                react_steps.append({"type": "observation", "content": f"Recovery: {recovery_result}"})
                        except Exception as recovery_exc:
                            messages.append({"role": "user", "content": f"Recovery failed: {recovery_exc}"})
                    else:
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

        if self.conversation_context:
            self.conversation_context.add_user_message(task)
            self.conversation_context.add_assistant_message(
                state.final_answer, react_steps=react_steps
            )

        return state
