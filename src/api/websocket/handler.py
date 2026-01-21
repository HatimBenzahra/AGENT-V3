import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

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
from src.tools.pdf_tool import CreatePDFTool
from src.tools.registry import ToolRegistry
from src.tools.terminal_tool import TerminalTool
from src.tools.vision_tool import VisionTool, ChartAnalyzerTool
from src.tools.web_search_tool import WebNewsSearchTool, WebSearchTool
from src.tools.knowledge_tool import KnowledgeSearchTool

active_connections: Dict[str, Dict[str, Any]] = {}


@dataclass
class PlanTask:
    id: str
    name: str
    status: str = "pending"


@dataclass
class PlanPhase:
    id: str
    name: str
    tasks: List[PlanTask] = field(default_factory=list)
    status: str = "pending"


@dataclass 
class ExecutionPlan:
    id: str
    title: str
    phases: List[PlanPhase] = field(default_factory=list)
    status: str = "pending"
    current_phase: int = 0
    current_task: int = 0
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "current_phase": self.current_phase,
            "current_task": self.current_task,
            "phases": [
                {
                    "id": p.id,
                    "name": p.name,
                    "status": p.status,
                    "tasks": [{"id": t.id, "name": t.name, "status": t.status} for t in p.tasks]
                }
                for p in self.phases
            ]
        }


@dataclass
class ConnectionState:
    websocket: WebSocket
    session: Session
    agent: ReActAgent
    is_processing: bool = False
    should_interrupt: bool = False
    current_task: Optional[asyncio.Task] = None
    current_plan: Optional[ExecutionPlan] = None


async def send_message(websocket: WebSocket, msg_type: str, **data):
    try:
        message = {"type": msg_type, **data}
        await websocket.send_json(message)
    except Exception as e:
        print(f"[WS] Failed to send {msg_type}: {e}")
        raise


async def create_session_with_tools(session_id: Optional[str] = None) -> tuple[Session, ToolRegistry]:
    if session_id and ConversationContext.exists(session_id):
        session = await Session.resume(session_id)
    else:
        session = await Session.create_new()

    registry = ToolRegistry()

    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    registry.register(WebNewsSearchTool())
    registry.register(HttpClientTool())
    registry.register(FetchWebPageTool())
    registry.register(KnowledgeSearchTool())

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
    registry.register(CreatePDFTool(
        execution_context=session.docker_context,
        conversation_context=session.context,
    ))

    registry.register(SaveOutputTool(conversation_context=session.context))
    registry.register(ListOutputsTool(conversation_context=session.context))
    
    registry.register(VisionTool(
        execution_context=session.docker_context,
        conversation_context=session.context,
    ))
    registry.register(ChartAnalyzerTool(
        execution_context=session.docker_context,
        conversation_context=session.context,
    ))

    return session, registry


def is_complex_task(task: str) -> bool:
    complex_keywords = [
        "rapport", "report", "pdf", "document", "créer", "create", "build",
        "projet", "project", "application", "app", "website", "site",
        "multiple", "plusieurs", "étapes", "steps", "pages", "latex",
        "graphique", "chart", "graph", "analyse", "analysis", "research"
    ]
    task_lower = task.lower()
    keyword_count = sum(1 for kw in complex_keywords if kw in task_lower)
    word_count = len(task.split())
    return keyword_count >= 2 or word_count > 30


async def generate_plan(task: str, llm_client) -> ExecutionPlan:
    prompt = f"""Analyze this task and create a structured execution plan.
Task: {task}

Return ONLY a JSON object with this exact structure (no markdown, no explanation):
{{
  "title": "Brief title",
  "phases": [
    {{
      "name": "Phase name",
      "tasks": ["Task 1", "Task 2"]
    }}
  ]
}}

Keep it concise: 2-4 phases, 2-4 tasks per phase."""

    response = await llm_client.chat_completion([
        {"role": "system", "content": "You are a task planner. Return only valid JSON."},
        {"role": "user", "content": prompt}
    ])
    
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            plan_data = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found")
    except:
        plan_data = {
            "title": task[:50] + "..." if len(task) > 50 else task,
            "phases": [{"name": "Execution", "tasks": ["Complete the task"]}]
        }
    
    import uuid
    plan = ExecutionPlan(
        id=str(uuid.uuid4())[:8],
        title=plan_data.get("title", "Task"),
        status="pending"
    )
    
    for i, phase_data in enumerate(plan_data.get("phases", [])):
        phase = PlanPhase(
            id=f"phase-{i+1}",
            name=phase_data.get("name", f"Phase {i+1}")
        )
        for j, task_name in enumerate(phase_data.get("tasks", [])):
            phase.tasks.append(PlanTask(
                id=f"task-{i+1}-{j+1}",
                name=task_name if isinstance(task_name, str) else str(task_name)
            ))
        plan.phases.append(phase)
    
    return plan


class StreamingReActAgent(ReActAgent):

    def __init__(
        self,
        tool_registry: ToolRegistry,
        conversation_context: Optional[ConversationContext] = None,
        websocket: Optional[WebSocket] = None,
        interrupt_check: Optional[Callable[[], bool]] = None,
        plan_getter: Optional[Callable[[], Optional[ExecutionPlan]]] = None,
    ):
        super().__init__(tool_registry, conversation_context)
        self.websocket = websocket
        self.interrupt_check = interrupt_check
        self.plan_getter = plan_getter
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    async def run_streaming(self, task: str) -> AgentState:
        state = AgentState(task=task)
        self._cancelled = False

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
        ]

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

        current_plan = self.plan_getter() if self.plan_getter else None
        if current_plan:
            plan_context = f"\n\nYou are executing this plan:\n{json.dumps(current_plan.to_dict(), indent=2)}\n\nExecute the tasks in order. Do not propose a new plan."
            messages.append({"role": "system", "content": plan_context})

        messages.append({"role": "user", "content": f"Task: {task}"})

        tool_names = {tool.name for tool in self.tools.get_all_tools()}
        react_steps = []

        while state.iteration < self.max_iterations and not state.is_complete:
            if self._cancelled or (self.interrupt_check and self.interrupt_check()):
                if self.websocket:
                    await send_message(self.websocket, "interrupted")
                state.set_final_answer("Task interrupted by user.")
                break

            state.iteration += 1
            
            if self.websocket:
                await send_message(self.websocket, "status", status="thinking")
            
            try:
                response = await asyncio.wait_for(
                    self.llm.chat_completion(messages),
                    timeout=120.0
                )
            except asyncio.TimeoutError:
                if self.websocket:
                    await send_message(self.websocket, "error", message="LLM timeout")
                state.set_final_answer("Request timed out.")
                break
            except asyncio.CancelledError:
                if self.websocket:
                    await send_message(self.websocket, "interrupted")
                state.set_final_answer("Task interrupted by user.")
                break

            if self._cancelled or (self.interrupt_check and self.interrupt_check()):
                if self.websocket:
                    await send_message(self.websocket, "interrupted")
                state.set_final_answer("Task interrupted by user.")
                break

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

                if self.websocket:
                    await send_message(self.websocket, "final_answer", content=final_answer or "")
                break

            if action_type in tool_names:
                if self._cancelled or (self.interrupt_check and self.interrupt_check()):
                    if self.websocket:
                        await send_message(self.websocket, "interrupted")
                    state.set_final_answer("Task interrupted by user.")
                    break
                    
                try:
                    tool = self.tools.get_tool(action_type)
                    action_payload = json.dumps(tool_params or {}, ensure_ascii=False)
                    state.add_action(f"{action_type}({action_payload})")
                    messages.append(
                        {"role": "assistant", "content": f"Action: {action_type}({action_payload})"}
                    )
                    react_steps.append({"type": "action", "tool": action_type, "params": tool_params})

                    if self.websocket:
                        await send_message(
                            self.websocket, "activity",
                            activity_type=self._get_activity_type(action_type),
                            tool=action_type,
                            params=tool_params or {},
                            status="running"
                        )

                    try:
                        result = await asyncio.wait_for(
                            tool.execute(**(tool_params or {})),
                            timeout=300.0
                        )
                    except asyncio.TimeoutError:
                        result = f"Tool {action_type} timed out after 5 minutes"
                    except asyncio.CancelledError:
                        if self.websocket:
                            await send_message(self.websocket, "interrupted")
                        state.set_final_answer("Task interrupted by user.")
                        break

                    state.add_observation(result)
                    messages.append({"role": "user", "content": f"Observation: {result}"})
                    react_steps.append({"type": "observation", "content": result})

                    if self.websocket:
                        file_created = None
                        if action_type == "write_file" and "File written successfully" in result:
                            file_path = (tool_params or {}).get("file_path", "")
                            file_content = (tool_params or {}).get("content", "")
                            file_created = {"path": file_path, "content": file_content}

                        await send_message(
                            self.websocket, "activity",
                            activity_type=self._get_activity_type(action_type),
                            tool=action_type,
                            result=result[:500] if len(result) > 500 else result,
                            status="completed",
                            file_created=file_created,
                        )

                except Exception as exc:
                    error_msg = f"Error executing {action_type}: {exc}"
                    state.add_observation(error_msg)
                    messages.append({"role": "user", "content": f"Observation: {error_msg}"})
                    react_steps.append({"type": "error", "content": error_msg})

                    if self.websocket:
                        await send_message(
                            self.websocket, "activity",
                            activity_type="error",
                            tool=action_type,
                            error=str(exc),
                            status="failed"
                        )
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

        if self.conversation_context:
            self.conversation_context.add_user_message(task)
            self.conversation_context.add_assistant_message(
                state.final_answer, react_steps=react_steps
            )

        return state

    def _get_activity_type(self, tool_name: str) -> str:
        activity_map = {
            "terminal": "terminal",
            "execute_command": "terminal",
            "write_file": "file",
            "read_file": "file",
            "list_directory": "file",
            "delete_file": "file",
            "web_search": "search",
            "news_search": "search",
            "fetch_webpage": "search",
            "http_request": "search",
            "create_pdf": "document",
            "calculator": "compute",
        }
        return activity_map.get(tool_name, "tool")


async def handle_websocket_message(
    websocket: WebSocket,
    message: Dict[str, Any],
    state: Dict[str, Any],
) -> None:
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
            if is_complex_task(content) and not state.get("current_plan"):
                await send_message(websocket, "status", status="planning")
                
                from src.models.llm_client import LLMClient
                llm = LLMClient()
                plan = await generate_plan(content, llm)
                state["current_plan"] = plan
                state["pending_task"] = content
                
                await send_message(
                    websocket, "plan_proposal",
                    plan=plan.to_dict(),
                    message="I've created an execution plan for your task. You can modify it or approve to start."
                )
                state["is_processing"] = False
                return

            agent = StreamingReActAgent(
                tool_registry=state["registry"],
                conversation_context=state["session"].context,
                websocket=websocket,
                interrupt_check=lambda: state["should_interrupt"],
                plan_getter=lambda: state.get("current_plan"),
            )
            
            state["active_agent"] = agent

            async def run_agent():
                try:
                    await send_message(websocket, "status", status="working")
                    result = await agent.run_streaming(content)
                    await send_message(websocket, "complete", task=content)
                except asyncio.CancelledError:
                    await send_message(websocket, "interrupted")
                except Exception as e:
                    await send_message(websocket, "error", message=str(e))
                finally:
                    state["is_processing"] = False
                    state["active_agent"] = None
                    state["current_task"] = None
                    if state.get("current_plan"):
                        state["current_plan"].status = "completed"

            task = asyncio.create_task(run_agent())
            state["current_task"] = task

        except Exception as e:
            await send_message(websocket, "error", message=str(e))
            state["is_processing"] = False

    elif msg_type == "approve_plan":
        plan = state.get("current_plan")
        pending_task = state.get("pending_task")
        
        if not plan or not pending_task:
            await send_message(websocket, "error", message="No plan to approve")
            return
        
        plan.status = "approved"
        state["is_processing"] = True
        
        agent = StreamingReActAgent(
            tool_registry=state["registry"],
            conversation_context=state["session"].context,
            websocket=websocket,
            interrupt_check=lambda: state["should_interrupt"],
            plan_getter=lambda: state.get("current_plan"),
        )
        
        state["active_agent"] = agent

        async def run_agent():
            try:
                await send_message(websocket, "status", status="working")
                await send_message(websocket, "plan_started", plan=plan.to_dict())
                result = await agent.run_streaming(pending_task)
                await send_message(websocket, "complete", task=pending_task)
            except asyncio.CancelledError:
                await send_message(websocket, "interrupted")
            except Exception as e:
                await send_message(websocket, "error", message=str(e))
            finally:
                state["is_processing"] = False
                state["active_agent"] = None
                state["current_task"] = None
                state["pending_task"] = None

        task = asyncio.create_task(run_agent())
        state["current_task"] = task

    elif msg_type == "update_plan":
        plan_data = message.get("plan")
        if not plan_data:
            await send_message(websocket, "error", message="No plan data provided")
            return
        
        current_plan = state.get("current_plan")
        if current_plan:
            current_plan.title = plan_data.get("title", current_plan.title)
            current_plan.phases = []
            for p in plan_data.get("phases", []):
                phase = PlanPhase(id=p["id"], name=p["name"])
                for t in p.get("tasks", []):
                    phase.tasks.append(PlanTask(id=t["id"], name=t["name"], status=t.get("status", "pending")))
                current_plan.phases.append(phase)
            
            await send_message(websocket, "plan_updated", plan=current_plan.to_dict())
            
            if state.get("active_agent"):
                pass

    elif msg_type == "interrupt":
        state["should_interrupt"] = True
        
        current_task = state.get("current_task")
        if current_task and not current_task.done():
            current_task.cancel()
        
        active_agent = state.get("active_agent")
        if active_agent:
            active_agent.cancel()
        
        await send_message(websocket, "interrupting")

    elif msg_type == "suggestion":
        suggestion = message.get("content", "")
        if suggestion and state.get("is_processing"):
            active_agent = state.get("active_agent")
            if active_agent and hasattr(active_agent, 'add_suggestion'):
                active_agent.add_suggestion(suggestion)
                await send_message(
                    websocket, "suggestion_received",
                    content=suggestion,
                    status="queued"
                )

    else:
        await send_message(websocket, "error", message=f"Unknown message type: {msg_type}")
