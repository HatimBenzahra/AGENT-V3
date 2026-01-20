"""Planning Agent for task decomposition and strategy creation."""
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.models.llm_client import LLMClient


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class StepType(Enum):
    """Types of plan steps."""
    RESEARCH = "research"  # Web search, information gathering
    FILE_CREATE = "file_create"  # Create files
    FILE_MODIFY = "file_modify"  # Modify existing files
    EXECUTE = "execute"  # Run commands
    VALIDATE = "validate"  # Verify results
    COMBINE = "combine"  # Combine outputs


@dataclass
class PlanStep:
    """A single step in a plan."""
    id: int
    description: str
    step_type: StepType
    tool: Optional[str] = None
    dependencies: List[int] = field(default_factory=list)
    expected_output: Optional[str] = None
    estimated_iterations: int = 1
    risk_level: str = "low"  # low, medium, high
    fallback: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "step_type": self.step_type.value,
            "tool": self.tool,
            "dependencies": self.dependencies,
            "expected_output": self.expected_output,
            "estimated_iterations": self.estimated_iterations,
            "risk_level": self.risk_level,
            "fallback": self.fallback,
        }


@dataclass
class Plan:
    """A complete execution plan."""
    task: str
    complexity: TaskComplexity
    summary: str
    steps: List[PlanStep]
    estimated_total_iterations: int
    resources_needed: List[str]
    potential_risks: List[str]
    success_criteria: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task": self.task,
            "complexity": self.complexity.value,
            "summary": self.summary,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_total_iterations": self.estimated_total_iterations,
            "resources_needed": self.resources_needed,
            "potential_risks": self.potential_risks,
            "success_criteria": self.success_criteria,
        }
        
    def to_markdown(self) -> str:
        """Convert to human-readable markdown."""
        lines = [
            f"# Plan: {self.task}",
            "",
            f"**Complexity**: {self.complexity.value}",
            f"**Estimated Iterations**: {self.estimated_total_iterations}",
            "",
            "## Summary",
            self.summary,
            "",
            "## Steps",
        ]
        
        for step in self.steps:
            deps = f" (depends on: {step.dependencies})" if step.dependencies else ""
            lines.append(f"{step.id}. **{step.description}**{deps}")
            lines.append(f"   - Type: {step.step_type.value}")
            if step.tool:
                lines.append(f"   - Tool: {step.tool}")
            if step.expected_output:
                lines.append(f"   - Expected: {step.expected_output}")
            lines.append("")
            
        if self.resources_needed:
            lines.append("## Resources Needed")
            for r in self.resources_needed:
                lines.append(f"- {r}")
            lines.append("")
            
        if self.potential_risks:
            lines.append("## Potential Risks")
            for r in self.potential_risks:
                lines.append(f"- {r}")
            lines.append("")
            
        if self.success_criteria:
            lines.append("## Success Criteria")
            for c in self.success_criteria:
                lines.append(f"- {c}")
                
        return "\n".join(lines)


class PlannerAgent:
    """Agent specialized in creating execution plans."""
    
    PLANNING_PROMPT = """You are a Planning Agent. Your job is to analyze tasks and create detailed execution plans.

Given a task, you must:
1. Assess complexity (simple/moderate/complex)
2. Identify required resources (libraries, APIs, files)
3. Break down into atomic steps
4. Identify dependencies between steps
5. Estimate iterations needed
6. Identify potential risks
7. Define success criteria

IMPORTANT RULES:
- Each step should be ONE atomic action
- For documents/articles: separate research, writing sections, charts, and final assembly
- For code: separate design, implementation, testing
- Be specific about which tool to use for each step
- Consider what could go wrong and have fallbacks

Available tools:
- web_search: Search the web for information
- news_search: Search for recent news
- write_file: Create or update files
- read_file: Read file contents
- execute_command: Run shell commands
- create_pdf: Create PDF documents
- fetch_webpage: Fetch and parse web pages

OUTPUT FORMAT (JSON):
{
    "complexity": "simple|moderate|complex",
    "summary": "Brief description of approach",
    "steps": [
        {
            "id": 1,
            "description": "What this step does",
            "step_type": "research|file_create|file_modify|execute|validate|combine",
            "tool": "tool_name or null",
            "dependencies": [step_ids],
            "expected_output": "What we expect",
            "estimated_iterations": 1,
            "risk_level": "low|medium|high",
            "fallback": "What to do if this fails"
        }
    ],
    "resources_needed": ["list of resources"],
    "potential_risks": ["list of risks"],
    "success_criteria": ["criteria for success"]
}

Respond ONLY with valid JSON."""

    def __init__(self):
        """Initialize planner agent."""
        self.llm = LLMClient()
        
    def _classify_task(self, task: str) -> TaskComplexity:
        """Quick classification of task complexity."""
        task_lower = task.lower()
        
        # Simple tasks
        simple_keywords = ["hello", "print", "simple", "create a file", "show", "list"]
        if any(kw in task_lower for kw in simple_keywords):
            return TaskComplexity.SIMPLE
            
        # Complex tasks
        complex_keywords = [
            "pdf", "report", "article", "document",
            "multiple", "pages", "charts", "graphs",
            "analysis", "compare", "research",
            "application", "website", "api"
        ]
        complex_count = sum(1 for kw in complex_keywords if kw in task_lower)
        
        if complex_count >= 2:
            return TaskComplexity.COMPLEX
        elif complex_count == 1:
            return TaskComplexity.MODERATE
            
        # Word count heuristic
        if len(task.split()) > 30:
            return TaskComplexity.COMPLEX
        elif len(task.split()) > 15:
            return TaskComplexity.MODERATE
            
        return TaskComplexity.SIMPLE
        
    async def create_plan(self, task: str) -> Plan:
        """Create an execution plan for a task.
        
        Args:
            task: The task description.
            
        Returns:
            Plan object with steps and metadata.
        """
        # Quick complexity assessment
        initial_complexity = self._classify_task(task)
        
        # For simple tasks, create a minimal plan
        if initial_complexity == TaskComplexity.SIMPLE:
            return self._create_simple_plan(task)
            
        # For complex tasks, use LLM to create detailed plan
        messages = [
            {"role": "system", "content": self.PLANNING_PROMPT},
            {"role": "user", "content": f"Create a detailed plan for this task:\n\n{task}"},
        ]
        
        response = await self.llm.chat_completion(messages)
        
        # Parse the JSON response
        try:
            # Extract JSON from response (might have markdown formatting)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                plan_data = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
                
            return self._parse_plan(task, plan_data)
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: create a generic plan
            print(f"[Planner] Failed to parse plan: {e}")
            return self._create_fallback_plan(task, initial_complexity)
            
    def _create_simple_plan(self, task: str) -> Plan:
        """Create a minimal plan for simple tasks."""
        return Plan(
            task=task,
            complexity=TaskComplexity.SIMPLE,
            summary="Simple task - direct execution",
            steps=[
                PlanStep(
                    id=1,
                    description="Execute the task directly",
                    step_type=StepType.EXECUTE,
                    estimated_iterations=2,
                )
            ],
            estimated_total_iterations=2,
            resources_needed=[],
            potential_risks=[],
            success_criteria=["Task completed successfully"],
        )
        
    def _create_fallback_plan(self, task: str, complexity: TaskComplexity) -> Plan:
        """Create a generic fallback plan."""
        task_lower = task.lower()
        steps = []
        step_id = 1
        
        # Determine task type and create appropriate steps
        if any(kw in task_lower for kw in ["pdf", "document", "report", "article"]):
            steps = [
                PlanStep(
                    id=step_id,
                    description="Research and gather information",
                    step_type=StepType.RESEARCH,
                    tool="web_search",
                    estimated_iterations=2,
                ),
                PlanStep(
                    id=step_id + 1,
                    description="Create document structure/outline",
                    step_type=StepType.FILE_CREATE,
                    tool="write_file",
                    dependencies=[step_id],
                    estimated_iterations=1,
                ),
                PlanStep(
                    id=step_id + 2,
                    description="Write content sections",
                    step_type=StepType.FILE_CREATE,
                    tool="write_file",
                    dependencies=[step_id + 1],
                    estimated_iterations=5,
                ),
                PlanStep(
                    id=step_id + 3,
                    description="Generate charts/visualizations if needed",
                    step_type=StepType.EXECUTE,
                    tool="execute_command",
                    dependencies=[step_id + 2],
                    estimated_iterations=3,
                ),
                PlanStep(
                    id=step_id + 4,
                    description="Create final PDF",
                    step_type=StepType.COMBINE,
                    tool="create_pdf",
                    dependencies=[step_id + 3],
                    estimated_iterations=2,
                ),
            ]
        elif any(kw in task_lower for kw in ["code", "script", "program", "function"]):
            steps = [
                PlanStep(
                    id=step_id,
                    description="Understand requirements and design solution",
                    step_type=StepType.RESEARCH,
                    estimated_iterations=1,
                ),
                PlanStep(
                    id=step_id + 1,
                    description="Write the code",
                    step_type=StepType.FILE_CREATE,
                    tool="write_file",
                    dependencies=[step_id],
                    estimated_iterations=2,
                ),
                PlanStep(
                    id=step_id + 2,
                    description="Test the code",
                    step_type=StepType.EXECUTE,
                    tool="execute_command",
                    dependencies=[step_id + 1],
                    estimated_iterations=2,
                ),
                PlanStep(
                    id=step_id + 3,
                    description="Validate output",
                    step_type=StepType.VALIDATE,
                    dependencies=[step_id + 2],
                    estimated_iterations=1,
                ),
            ]
        else:
            steps = [
                PlanStep(
                    id=step_id,
                    description="Analyze task requirements",
                    step_type=StepType.RESEARCH,
                    estimated_iterations=1,
                ),
                PlanStep(
                    id=step_id + 1,
                    description="Execute main task",
                    step_type=StepType.EXECUTE,
                    dependencies=[step_id],
                    estimated_iterations=3,
                ),
                PlanStep(
                    id=step_id + 2,
                    description="Verify results",
                    step_type=StepType.VALIDATE,
                    dependencies=[step_id + 1],
                    estimated_iterations=1,
                ),
            ]
            
        total_iterations = sum(s.estimated_iterations for s in steps)
        
        return Plan(
            task=task,
            complexity=complexity,
            summary=f"Fallback plan for {complexity.value} task",
            steps=steps,
            estimated_total_iterations=total_iterations,
            resources_needed=[],
            potential_risks=["Plan is generic - may need adjustment"],
            success_criteria=["Task completed without errors"],
        )
        
    def _parse_plan(self, task: str, data: Dict[str, Any]) -> Plan:
        """Parse plan data from LLM response."""
        # Parse complexity
        complexity_str = data.get("complexity", "moderate").lower()
        complexity_map = {
            "simple": TaskComplexity.SIMPLE,
            "moderate": TaskComplexity.MODERATE,
            "complex": TaskComplexity.COMPLEX,
        }
        complexity = complexity_map.get(complexity_str, TaskComplexity.MODERATE)
        
        # Parse steps
        steps = []
        for step_data in data.get("steps", []):
            step_type_str = step_data.get("step_type", "execute").lower()
            step_type_map = {
                "research": StepType.RESEARCH,
                "file_create": StepType.FILE_CREATE,
                "file_modify": StepType.FILE_MODIFY,
                "execute": StepType.EXECUTE,
                "validate": StepType.VALIDATE,
                "combine": StepType.COMBINE,
            }
            step_type = step_type_map.get(step_type_str, StepType.EXECUTE)
            
            steps.append(PlanStep(
                id=step_data.get("id", len(steps) + 1),
                description=step_data.get("description", ""),
                step_type=step_type,
                tool=step_data.get("tool"),
                dependencies=step_data.get("dependencies", []),
                expected_output=step_data.get("expected_output"),
                estimated_iterations=step_data.get("estimated_iterations", 1),
                risk_level=step_data.get("risk_level", "low"),
                fallback=step_data.get("fallback"),
            ))
            
        total_iterations = sum(s.estimated_iterations for s in steps)
        
        return Plan(
            task=task,
            complexity=complexity,
            summary=data.get("summary", ""),
            steps=steps,
            estimated_total_iterations=total_iterations,
            resources_needed=data.get("resources_needed", []),
            potential_risks=data.get("potential_risks", []),
            success_criteria=data.get("success_criteria", []),
        )
        
    def estimate_complexity(self, task: str) -> Dict[str, Any]:
        """Quick complexity estimate without full planning.
        
        Args:
            task: The task description.
            
        Returns:
            Dictionary with complexity info.
        """
        complexity = self._classify_task(task)
        
        # Estimate based on complexity
        estimates = {
            TaskComplexity.SIMPLE: {"iterations": 3, "time": "< 1 min"},
            TaskComplexity.MODERATE: {"iterations": 10, "time": "1-3 min"},
            TaskComplexity.COMPLEX: {"iterations": 30, "time": "3-10 min"},
        }
        
        return {
            "complexity": complexity.value,
            "estimated_iterations": estimates[complexity]["iterations"],
            "estimated_time": estimates[complexity]["time"],
            "needs_planning": complexity != TaskComplexity.SIMPLE,
        }
