"""Multi-Agent Orchestrator for coordinating planning, execution, and validation."""
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from src.agent.planner import Plan, PlannerAgent, PlanStep, TaskComplexity
from src.agent.validator import OutputValidator, TaskValidator, ValidationStatus
from src.agent.recovery import RecoveryManager
from src.agent.state import AgentState
from src.models.llm_client import LLMClient
from src.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from fastapi import WebSocket
    from src.session.conversation_context import ConversationContext


class ExecutionMode(Enum):
    """Execution modes for the orchestrator."""
    DIRECT = "direct"  # Execute without planning (simple tasks)
    PLANNED = "planned"  # Execute with planning (complex tasks)
    INTERACTIVE = "interactive"  # Plan + user approval before execution


@dataclass
class StepResult:
    """Result of executing a plan step."""
    step_id: int
    success: bool
    observation: str
    iterations_used: int
    validation_status: ValidationStatus


@dataclass
class ExecutionResult:
    """Complete execution result."""
    task: str
    mode: ExecutionMode
    plan: Optional[Plan]
    step_results: List[StepResult]
    final_answer: str
    total_iterations: int
    success: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task": self.task,
            "mode": self.mode.value,
            "plan": self.plan.to_dict() if self.plan else None,
            "step_results": [
                {
                    "step_id": sr.step_id,
                    "success": sr.success,
                    "observation": sr.observation[:200],
                    "iterations_used": sr.iterations_used,
                    "validation_status": sr.validation_status.value,
                }
                for sr in self.step_results
            ],
            "final_answer": self.final_answer,
            "total_iterations": self.total_iterations,
            "success": self.success,
        }


class AgentOrchestrator:
    """Orchestrates multiple agents for task execution.
    
    Flow:
    1. Analyze task complexity
    2. Create plan (if complex)
    3. Execute plan steps
    4. Validate results
    5. Recovery if needed
    6. Compile final answer
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        conversation_context: Optional["ConversationContext"] = None,
        websocket: Optional["WebSocket"] = None,
        mode: ExecutionMode = ExecutionMode.PLANNED,
    ):
        """Initialize orchestrator.
        
        Args:
            tool_registry: Registry of available tools.
            conversation_context: Conversation context for persistence.
            websocket: WebSocket for streaming updates.
            mode: Execution mode.
        """
        self.tools = tool_registry
        self.conversation_context = conversation_context
        self.websocket = websocket
        self.mode = mode
        
        # Initialize sub-agents
        self.planner = PlannerAgent()
        self.validator = OutputValidator()
        self.task_validator = TaskValidator()
        self.recovery_manager = RecoveryManager()
        self.llm = LLMClient()
        
        # Callbacks for HITL
        self.on_plan_created: Optional[Callable[[Plan], None]] = None
        self.on_step_started: Optional[Callable[[PlanStep], None]] = None
        self.on_step_completed: Optional[Callable[[StepResult], None]] = None
        self.pending_suggestions: List[str] = []
        
    async def _notify(self, msg_type: str, **data):
        """Send notification via websocket if available."""
        if self.websocket:
            try:
                await self.websocket.send_json({"type": msg_type, **data})
            except Exception:
                pass
                
    def add_suggestion(self, suggestion: str):
        """Add a user suggestion."""
        self.pending_suggestions.append(suggestion)
        
    async def execute(self, task: str) -> ExecutionResult:
        """Execute a task using the multi-agent system.
        
        Args:
            task: The task to execute.
            
        Returns:
            ExecutionResult with complete execution details.
        """
        # Reset for new task
        self.task_validator.reset()
        self.recovery_manager.reset()
        
        # Analyze complexity
        complexity_info = self.planner.estimate_complexity(task)
        await self._notify("complexity_assessed", **complexity_info)
        
        # Decide execution mode
        if complexity_info["complexity"] == "simple" and self.mode != ExecutionMode.INTERACTIVE:
            return await self._execute_direct(task)
        else:
            return await self._execute_planned(task)
            
    async def _execute_direct(self, task: str) -> ExecutionResult:
        """Execute simple task directly without detailed planning."""
        state = AgentState(task=task)
        
        # Simple execution using ReAct pattern
        messages = [
            {"role": "system", "content": self._build_executor_prompt()},
            {"role": "user", "content": f"Task: {task}"},
        ]
        
        iterations = 0
        max_iterations = 20  # Lower for simple tasks
        
        while iterations < max_iterations and not state.is_complete:
            iterations += 1
            
            response = await self.llm.chat_completion(messages)
            
            # Parse and execute (simplified)
            action_result = await self._execute_response(response, messages, state)
            
            if action_result.get("is_final"):
                state.set_final_answer(action_result.get("answer", ""))
                break
                
        return ExecutionResult(
            task=task,
            mode=ExecutionMode.DIRECT,
            plan=None,
            step_results=[],
            final_answer=state.final_answer or "Task completed.",
            total_iterations=iterations,
            success=state.is_complete,
        )
        
    async def _execute_planned(self, task: str) -> ExecutionResult:
        """Execute task with detailed planning."""
        # Create plan
        await self._notify("planning_started", task=task)
        plan = await self.planner.create_plan(task)
        await self._notify("plan_created", plan=plan.to_dict())
        
        # Callback for HITL
        if self.on_plan_created:
            self.on_plan_created(plan)
            
        # Interactive mode: wait for approval
        if self.mode == ExecutionMode.INTERACTIVE:
            await self._notify("plan_pending_approval", plan=plan.to_markdown())
            # In a real implementation, we'd wait for user approval here
            
        # Execute plan steps
        step_results: List[StepResult] = []
        total_iterations = 0
        
        for step in plan.steps:
            # Check dependencies
            dependencies_met = all(
                any(sr.step_id == dep and sr.success for sr in step_results)
                for dep in step.dependencies
            )
            
            if not dependencies_met and step.dependencies:
                step_results.append(StepResult(
                    step_id=step.id,
                    success=False,
                    observation="Dependencies not met",
                    iterations_used=0,
                    validation_status=ValidationStatus.SKIPPED,
                ))
                continue
                
            # Execute step
            if self.on_step_started:
                self.on_step_started(step)
            await self._notify("step_started", step=step.to_dict())
            
            result = await self._execute_step(step, plan, step_results)
            step_results.append(result)
            total_iterations += result.iterations_used
            
            if self.on_step_completed:
                self.on_step_completed(result)
            await self._notify("step_completed", result={
                "step_id": result.step_id,
                "success": result.success,
                "observation": result.observation[:200],
            })
            
            # Handle failure
            if not result.success and step.fallback:
                await self._notify("executing_fallback", step_id=step.id, fallback=step.fallback)
                
        # Assess overall task completion
        task_validation = self.task_validator.assess_task_completion(
            task=task,
            final_answer=self._compile_final_answer(plan, step_results),
        )
        
        final_answer = self._compile_final_answer(plan, step_results)
        
        return ExecutionResult(
            task=task,
            mode=ExecutionMode.PLANNED,
            plan=plan,
            step_results=step_results,
            final_answer=final_answer,
            total_iterations=total_iterations,
            success=task_validation.status == ValidationStatus.VALID,
        )
        
    async def _execute_step(
        self,
        step: PlanStep,
        plan: Plan,
        previous_results: List[StepResult],
    ) -> StepResult:
        """Execute a single plan step."""
        iterations = 0
        max_iterations = step.estimated_iterations * 2  # Allow some buffer
        
        # Build context for this step
        context = self._build_step_context(step, plan, previous_results)
        
        messages = [
            {"role": "system", "content": self._build_executor_prompt()},
            {"role": "system", "content": context},
            {"role": "user", "content": f"Execute this step: {step.description}"},
        ]
        
        last_observation = ""
        success = False
        
        while iterations < max_iterations:
            iterations += 1
            
            # Check for suggestions
            if self.pending_suggestions:
                for suggestion in self.pending_suggestions:
                    messages.append({
                        "role": "user",
                        "content": f"[USER SUGGESTION] {suggestion}"
                    })
                self.pending_suggestions.clear()
                
            response = await self.llm.chat_completion(messages)
            result = await self._execute_response(response, messages, None)
            
            last_observation = result.get("observation", "")
            
            # Validate result
            if result.get("action") and result.get("params"):
                validation = await self.validator.validate(
                    action=result["action"],
                    result=last_observation,
                    params=result["params"],
                )
                
                self.task_validator.record_action(
                    action=result["action"],
                    params=result["params"],
                    result=last_observation,
                    validation=validation,
                )
                
                if validation.status == ValidationStatus.VALID:
                    success = True
                    break
                elif validation.status == ValidationStatus.INVALID:
                    # Try recovery
                    recovery = self.recovery_manager.analyze_error(
                        error_message=last_observation,
                        action=result["action"],
                        params=result["params"],
                    )
                    if recovery:
                        messages.append({
                            "role": "user",
                            "content": f"[RECOVERY] {recovery.description}"
                        })
                        
            if result.get("is_final"):
                success = True
                break
                
        return StepResult(
            step_id=step.id,
            success=success,
            observation=last_observation,
            iterations_used=iterations,
            validation_status=ValidationStatus.VALID if success else ValidationStatus.INVALID,
        )
        
    def _build_executor_prompt(self) -> str:
        """Build prompt for the executor agent."""
        tools = self.tools.get_tools_schema()
        tool_descriptions = []
        for tool in tools:
            func = tool['function']
            name = func['name']
            desc = func['description']
            tool_descriptions.append(f"- {name}: {desc}")
            
        tool_lines = "\n".join(tool_descriptions)
        
        return f"""You are an Executor Agent. You execute specific steps from a plan.

TOOLS:
{tool_lines}

FORMAT:
Thought: <reasoning>
Action: tool_name({{"param": "value"}})

When step is complete:
Action: Final Answer: <result summary>

RULES:
- Focus on the current step only
- Be efficient and direct
- Report any errors encountered
"""

    def _build_step_context(
        self,
        step: PlanStep,
        plan: Plan,
        previous_results: List[StepResult],
    ) -> str:
        """Build context for a step execution."""
        lines = [
            f"OVERALL TASK: {plan.task}",
            f"CURRENT STEP: {step.id}/{len(plan.steps)} - {step.description}",
        ]
        
        if step.tool:
            lines.append(f"SUGGESTED TOOL: {step.tool}")
            
        if step.expected_output:
            lines.append(f"EXPECTED OUTPUT: {step.expected_output}")
            
        if previous_results:
            lines.append("\nPREVIOUS RESULTS:")
            for pr in previous_results[-3:]:  # Last 3 results
                status = "OK" if pr.success else "FAILED"
                lines.append(f"  Step {pr.step_id}: {status}")
                
        return "\n".join(lines)
        
    def _compile_final_answer(
        self,
        plan: Plan,
        results: List[StepResult],
    ) -> str:
        """Compile the final answer from step results."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        lines = [f"Task: {plan.task}", ""]
        
        if successful:
            lines.append("Completed steps:")
            for r in successful:
                step = next((s for s in plan.steps if s.id == r.step_id), None)
                if step:
                    lines.append(f"  - {step.description}")
                    
        if failed:
            lines.append("\nFailed steps:")
            for r in failed:
                step = next((s for s in plan.steps if s.id == r.step_id), None)
                if step:
                    lines.append(f"  - {step.description}: {r.observation[:100]}")
                    
        # Include any file paths from observations
        for r in successful:
            if "Download URL" in r.observation or "written" in r.observation.lower():
                lines.append(f"\nOutput: {r.observation}")
                break
                
        return "\n".join(lines)
        
    async def _execute_response(
        self,
        response: str,
        messages: List[Dict[str, str]],
        state: Optional[AgentState],
    ) -> Dict[str, Any]:
        """Parse and execute an LLM response."""
        import re
        import json
        
        result = {
            "is_final": False,
            "action": None,
            "params": None,
            "observation": "",
            "answer": None,
        }
        
        # Extract thought
        thought_match = re.search(
            r"Thought:\s*(.+?)(?=Action:|$)", response, re.DOTALL | re.IGNORECASE
        )
        if thought_match:
            thought = thought_match.group(1).strip()
            messages.append({"role": "assistant", "content": f"Thought: {thought}"})
            if state:
                state.add_thought(thought)
                
        # Parse action
        action_match = re.search(r"Action:\s*(.+)", response, re.IGNORECASE)
        if not action_match:
            return result
            
        action_text = action_match.group(1).strip()
        
        # Check for final answer
        if "final answer:" in action_text.lower():
            result["is_final"] = True
            result["answer"] = action_text.split(":", 1)[1].strip() if ":" in action_text else action_text
            return result
            
        # Parse tool call
        tool_match = re.match(r"(\w+)\((.*)\)", action_text, re.DOTALL)
        if tool_match:
            tool_name = tool_match.group(1)
            params_text = tool_match.group(2).strip()
            
            try:
                params = json.loads(params_text) if params_text else {}
            except json.JSONDecodeError:
                params = {}
                
            result["action"] = tool_name
            result["params"] = params
            
            # Execute tool
            tool = self.tools.get_tool(tool_name)
            if tool:
                try:
                    observation = await tool.execute(**params)
                    result["observation"] = observation
                    messages.append({
                        "role": "assistant",
                        "content": f"Action: {tool_name}({json.dumps(params)})"
                    })
                    messages.append({
                        "role": "user",
                        "content": f"Observation: {observation}"
                    })
                    if state:
                        state.add_action(f"{tool_name}({params_text})")
                        state.add_observation(observation)
                except Exception as e:
                    result["observation"] = f"Error: {e}"
                    messages.append({
                        "role": "user",
                        "content": f"Observation: Error: {e}"
                    })
                    
        return result
