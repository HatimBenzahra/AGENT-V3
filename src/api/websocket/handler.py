"""WebSocket message handler for real-time agent communication."""
import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from fastapi import WebSocket

from src.agent.react_agent import ReActAgent
from src.agent.state import AgentState
from src.config import Config
from src.execution.docker_context import DockerExecutionContext
from src.session.conversation_context import ConversationContext
from src.session.session_manager import Session
from src.tools.calculator import CalculatorTool
from src.tools.file_tools import (
    DeleteFileTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from src.tools.http_tool import FetchWebPageTool, HttpClientTool
from src.tools.output_tool import ListOutputsTool, SaveOutputTool
from src.tools.registry import ToolRegistry
from src.tools.terminal_tool import TerminalTool
from src.tools.web_search_tool import WebNewsSearchTool, WebSearchTool

# Active WebSocket connections: session_id -> connection info
active_connections: Dict[str, Dict[str, Any]] = {}


@dataclass
class ConnectionState:
    """State for a WebSocket connection."""

    websocket: WebSocket
    session: Session
    agent: ReActAgent
    is_processing: bool = False
    should_interrupt: bool = False


async def send_message(websocket: WebSocket, msg_type: str, **data):
    """Send a typed message to the client, handling closed connections gracefully."""
    try:
        message = {"type": msg_type, **data}
        await websocket.send_json(message)
    except Exception as e:
        # Connection might be closed, log but don't raise
        print(f"[WS] Failed to send {msg_type}: {e}")
        raise


async def create_session_with_tools(session_id: Optional[str] = None) -> tuple[Session, ToolRegistry]:
    """Create a session with all tools registered."""
    if session_id and ConversationContext.exists(session_id):
        session = await Session.resume(session_id)
    else:
        session = await Session.create_new()

    # Register all tools
    registry = ToolRegistry()

    # Context-free tools
    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    registry.register(WebNewsSearchTool())
    registry.register(HttpClientTool())
    registry.register(FetchWebPageTool())

    # Docker-dependent tools
    registry.register(TerminalTool(
        execution_context=session.docker_context,
        conversation_context=session.context,
    ))
    registry.register(ReadFileTool(
        execution_context=session.docker_context,
        conversation_context=session.context,
    ))
    registry.register(WriteFileTool(
        execution_context=session.docker_context,
        conversation_context=session.context,
    ))
    registry.register(ListDirectoryTool(
        execution_context=session.docker_context,
        conversation_context=session.context,
    ))
    registry.register(DeleteFileTool(
        execution_context=session.docker_context,
        conversation_context=session.context,
    ))

    # Context-dependent tools
    registry.register(SaveOutputTool(conversation_context=session.context))
    registry.register(ListOutputsTool(conversation_context=session.context))

    return session, registry


class StreamingReActAgent(ReActAgent):
    """ReAct Agent with streaming support for WebSocket."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        conversation_context: Optional[ConversationContext] = None,
        websocket: Optional[WebSocket] = None,
        interrupt_check: Optional[Callable[[], bool]] = None,
    ):
        super().__init__(tool_registry, conversation_context)
        self.websocket = websocket
        self.interrupt_check = interrupt_check

    async def run_streaming(self, task: str) -> AgentState:
        """Run the ReAct loop with streaming to WebSocket."""
        state = AgentState(task=task)

        # Build initial messages
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
        ]

        # Add recent conversation history for context
        history = self._get_conversation_history_messages()
        if history:
            messages.append({
                "role": "system",
                "content": "Previous conversation context:\n" + "\n".join(
                    [f"{m['role']}: {m['content'][:200]}..."
                     if len(m['content']) > 200 else f"{m['role']}: {m['content']}"
                     for m in history[-5:]]
                )
            })

        messages.append({"role": "user", "content": f"Task: {task}"})

        tool_names = {tool.name for tool in self.tools.get_all_tools()}
        react_steps = []

        while state.iteration < self.max_iterations and not state.is_complete:
            # Check for interrupt
            if self.interrupt_check and self.interrupt_check():
                if self.websocket:
                    await send_message(self.websocket, "interrupted")
                state.set_final_answer("Task interrupted by user.")
                break

            state.iteration += 1
            response = await self.llm.chat_completion(messages)

            # Extract and stream thought
            thought_match = re.search(
                r"Thought:\s*(.+?)(?=Action:|$)", response, re.DOTALL | re.IGNORECASE
            )
            if thought_match:
                thought = thought_match.group(1).strip()
                state.add_thought(thought)
                messages.append({"role": "assistant", "content": f"Thought: {thought}"})
                react_steps.append({"type": "thought", "content": thought})

                # Stream thought to client
                if self.websocket:
                    await send_message(self.websocket, "thought", content=thought)

            # Parse action
            action_type, final_answer, tool_params = self._parse_action(response)

            if action_type == "final_answer":
                state.set_final_answer(final_answer or "")
                messages.append(
                    {"role": "assistant", "content": f"Final Answer: {final_answer or ''}"}
                )
                react_steps.append({"type": "final_answer", "content": final_answer or ""})

                # Stream final answer
                if self.websocket:
                    await send_message(self.websocket, "final_answer", content=final_answer or "")
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

                    # Stream action to client
                    if self.websocket:
                        await send_message(
                            self.websocket, "action",
                            tool=action_type,
                            params=tool_params or {}
                        )

                    # Execute tool
                    result = await tool.execute(**(tool_params or {}))
                    state.add_observation(result)
                    messages.append({"role": "user", "content": f"Observation: {result}"})
                    react_steps.append({"type": "observation", "content": result})

                    # Stream observation to client
                    if self.websocket:
                        # Check if file was created
                        file_created = None
                        if action_type == "write_file" and "File written successfully" in result:
                            file_path = tool_params.get("file_path", "")
                            file_content = tool_params.get("content", "")
                            file_created = {"path": file_path, "content": file_content}

                        await send_message(
                            self.websocket, "observation",
                            content=result,
                            tool=action_type,
                            file_created=file_created,
                        )

                except Exception as exc:
                    error_msg = f"Error executing {action_type}: {exc}"
                    state.add_observation(error_msg)
                    messages.append({"role": "user", "content": f"Observation: {error_msg}"})
                    react_steps.append({"type": "error", "content": error_msg})

                    if self.websocket:
                        await send_message(self.websocket, "error", message=error_msg)
                continue

            error_msg = (
                "Invalid action format. Use: "
                "Action: tool_name({\"param\": \"value\"}) or Action: Final Answer: <answer>"
            )
            state.add_observation(error_msg)
            messages.append({"role": "user", "content": f"Observation: {error_msg}"})

        if not state.is_complete and state.iteration >= self.max_iterations:
            msg = "Maximum iterations reached. Unable to complete the task."
            state.set_final_answer(msg)
            if self.websocket:
                await send_message(self.websocket, "final_answer", content=msg)

        # Save to conversation context
        if self.conversation_context:
            self.conversation_context.add_user_message(task)
            self.conversation_context.add_assistant_message(
                state.final_answer, react_steps=react_steps
            )

        return state


async def handle_websocket_message(
    websocket: WebSocket,
    message: Dict[str, Any],
    state: Dict[str, Any],
) -> None:
    """Handle incoming WebSocket message."""
    msg_type = message.get("type")

    if msg_type == "chat":
        content = message.get("content", "")
        if not content:
            await send_message(websocket, "error", message="Empty message")
            return

        if state["is_processing"]:
            await send_message(websocket, "error", message="Agent is already processing")
            return

        state["is_processing"] = True
        state["should_interrupt"] = False

        try:
            # Create streaming agent
            agent = StreamingReActAgent(
                tool_registry=state["registry"],
                conversation_context=state["session"].context,
                websocket=websocket,
                interrupt_check=lambda: state["should_interrupt"],
            )

            # Run agent
            await send_message(websocket, "processing", task=content)
            result = await agent.run_streaming(content)

            # Send completion
            await send_message(websocket, "complete", task=content)

        except Exception as e:
            try:
                await send_message(websocket, "error", message=str(e))
            except Exception:
                # Connection closed, can't send error
                pass
        finally:
            state["is_processing"] = False

    elif msg_type == "interrupt":
        if state["is_processing"]:
            state["should_interrupt"] = True
            await send_message(websocket, "interrupting")

    elif msg_type == "suggestion":
        # Handle user suggestion during processing
        suggestion = message.get("content", "")
        if suggestion:
            # For now, just acknowledge - could be used to modify agent behavior
            await send_message(websocket, "suggestion_received", content=suggestion)

    else:
        await send_message(websocket, "error", message=f"Unknown message type: {msg_type}")
