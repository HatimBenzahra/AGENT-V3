from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


class PlanStatus(Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class Task:
    name: str
    done_when: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TaskStatus = TaskStatus.PENDING
    notes: str = ""
    output: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "done_when": self.done_when,
            "status": self.status.value,
            "notes": self.notes,
            "output": self.output,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data["name"],
            done_when=data.get("done_when", ""),
            status=TaskStatus(data.get("status", "pending")),
            notes=data.get("notes", ""),
            output=data.get("output"),
        )


@dataclass
class Phase:
    name: str
    objective: str
    tasks: List[Task]
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    order: int = 0
    depends_on: List[str] = field(default_factory=list)
    
    @property
    def status(self) -> TaskStatus:
        if not self.tasks:
            return TaskStatus.PENDING
        
        statuses = [t.status for t in self.tasks]
        
        if all(s == TaskStatus.COMPLETED for s in statuses):
            return TaskStatus.COMPLETED
        if any(s == TaskStatus.FAILED for s in statuses):
            return TaskStatus.FAILED
        if any(s == TaskStatus.IN_PROGRESS for s in statuses):
            return TaskStatus.IN_PROGRESS
        return TaskStatus.PENDING
    
    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "objective": self.objective,
            "order": self.order,
            "depends_on": self.depends_on,
            "tasks": [t.to_dict() for t in self.tasks],
            "status": self.status.value,
            "progress": self.progress,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Phase":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data["name"],
            objective=data.get("objective", ""),
            order=data.get("order", 0),
            depends_on=data.get("depends_on", []),
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
        )


@dataclass
class Deliverable:
    name: str
    format: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "format": self.format,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Deliverable":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data["name"],
            format=data.get("format", ""),
            description=data.get("description", ""),
        )


@dataclass
class ProjectPlan:
    title: str
    objective: str
    phases: List[Phase]
    deliverables: List[Deliverable]
    original_request: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: PlanStatus = PlanStatus.DRAFT
    deadline: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    resources_provided: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    user_modified: bool = False
    
    @property
    def total_tasks(self) -> int:
        return sum(len(p.tasks) for p in self.phases)
    
    @property
    def completed_tasks(self) -> int:
        return sum(
            1 for p in self.phases 
            for t in p.tasks 
            if t.status == TaskStatus.COMPLETED
        )
    
    @property
    def progress(self) -> float:
        total = self.total_tasks
        if total == 0:
            return 0.0
        return self.completed_tasks / total
    
    @property
    def current_phase(self) -> Optional[Phase]:
        for phase in self.phases:
            if phase.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                return phase
        return None
    
    @property
    def current_task(self) -> Optional[Task]:
        phase = self.current_phase
        if not phase:
            return None
        for task in phase.tasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                return task
        return None
    
    def get_phase_by_id(self, phase_id: str) -> Optional[Phase]:
        for phase in self.phases:
            if phase.id == phase_id:
                return phase
        return None
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        for phase in self.phases:
            for task in phase.tasks:
                if task.id == task_id:
                    return task
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "objective": self.objective,
            "original_request": self.original_request,
            "status": self.status.value,
            "deadline": self.deadline,
            "constraints": self.constraints,
            "resources_provided": self.resources_provided,
            "deliverables": [d.to_dict() for d in self.deliverables],
            "phases": [p.to_dict() for p in self.phases],
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "progress": self.progress,
            "created_at": self.created_at,
            "user_modified": self.user_modified,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectPlan":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            title=data["title"],
            objective=data.get("objective", ""),
            original_request=data.get("original_request", ""),
            status=PlanStatus(data.get("status", "draft")),
            deadline=data.get("deadline"),
            constraints=data.get("constraints", []),
            resources_provided=data.get("resources_provided", []),
            deliverables=[Deliverable.from_dict(d) for d in data.get("deliverables", [])],
            phases=[Phase.from_dict(p) for p in data.get("phases", [])],
            created_at=data.get("created_at", datetime.now().isoformat()),
            user_modified=data.get("user_modified", False),
        )
    
    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"**Objectif:** {self.objective}",
            "",
        ]
        
        if self.deadline:
            lines.append(f"**Deadline:** {self.deadline}")
            lines.append("")
        
        if self.deliverables:
            lines.append("## Livrables attendus")
            for d in self.deliverables:
                lines.append(f"- **{d.name}** ({d.format}): {d.description}")
            lines.append("")
        
        if self.constraints:
            lines.append("## Contraintes")
            for c in self.constraints:
                lines.append(f"- {c}")
            lines.append("")
        
        lines.append("## Plan d'exécution")
        lines.append("")
        
        for i, phase in enumerate(self.phases, 1):
            status_icon = {
                TaskStatus.COMPLETED: "✅",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.FAILED: "❌",
                TaskStatus.PENDING: "⏳",
                TaskStatus.SKIPPED: "⏭️",
            }.get(phase.status, "⏳")
            
            lines.append(f"### Phase {i}: {phase.name} {status_icon}")
            lines.append(f"*{phase.objective}*")
            lines.append("")
            
            for task in phase.tasks:
                task_icon = {
                    TaskStatus.COMPLETED: "✅",
                    TaskStatus.IN_PROGRESS: "🔄",
                    TaskStatus.FAILED: "❌",
                    TaskStatus.PENDING: "⬜",
                    TaskStatus.SKIPPED: "⏭️",
                }.get(task.status, "⬜")
                
                lines.append(f"- {task_icon} **{task.name}**")
                if task.done_when:
                    lines.append(f"  - *Done when:* {task.done_when}")
            
            lines.append("")
        
        return "\n".join(lines)
