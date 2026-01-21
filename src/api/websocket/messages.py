from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class MessageType(Enum):
    CHAT = "chat"
    INTERRUPT = "interrupt"
    SUGGESTION = "suggestion"
    REQUEST_PLAN = "request_plan"
    APPROVE_PLAN = "approve_plan"
    UPDATE_PLAN = "update_plan"
    PAUSE_EXECUTION = "pause_execution"
    RESUME_EXECUTION = "resume_execution"
    
    PROCESSING = "processing"
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL_ANSWER = "final_answer"
    ERROR = "error"
    COMPLETE = "complete"
    INTERRUPTED = "interrupted"
    
    PROJECT_ANALYZING = "project_analyzing"
    PROJECT_PLANNING = "project_planning"
    PROJECT_PLAN_CREATED = "project_plan_created"
    PROJECT_PLAN_UPDATED = "project_plan_updated"
    PROJECT_PENDING_APPROVAL = "project_pending_approval"
    PROJECT_EXECUTION_STARTED = "project_execution_started"
    PROJECT_PAUSED = "project_paused"
    PROJECT_RESUMED = "project_resumed"
    PROJECT_COMPLETED = "project_completed"
    PROJECT_FAILED = "project_failed"
    
    DELIVERABLE_STARTED = "deliverable_started"
    DELIVERABLE_COMPLETED = "deliverable_completed"
    
    SECTION_STARTED = "section_started"
    SECTION_COMPLETED = "section_completed"


@dataclass
class BaseMessage:
    type: MessageType
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value}


@dataclass
class ChatMessage(BaseMessage):
    content: str
    type: MessageType = field(default=MessageType.CHAT)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value, "content": self.content}


@dataclass
class SuggestionMessage(BaseMessage):
    content: str
    type: MessageType = field(default=MessageType.SUGGESTION)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value, "content": self.content}


@dataclass
class RequestPlanMessage(BaseMessage):
    content: str
    type: MessageType = field(default=MessageType.REQUEST_PLAN)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value, "content": self.content}


@dataclass
class ApprovePlanMessage(BaseMessage):
    type: MessageType = field(default=MessageType.APPROVE_PLAN)


@dataclass
class UpdatePlanMessage(BaseMessage):
    modifications: Dict[str, Any]
    type: MessageType = field(default=MessageType.UPDATE_PLAN)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value, "modifications": self.modifications}


@dataclass
class ProjectPlanCreatedMessage(BaseMessage):
    plan: Dict[str, Any]
    plan_markdown: str
    type: MessageType = field(default=MessageType.PROJECT_PLAN_CREATED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "plan": self.plan,
            "plan_markdown": self.plan_markdown,
        }


@dataclass
class ProjectPlanUpdatedMessage(BaseMessage):
    plan: Dict[str, Any]
    type: MessageType = field(default=MessageType.PROJECT_PLAN_UPDATED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value, "plan": self.plan}


@dataclass
class DeliverableStartedMessage(BaseMessage):
    deliverable_id: str
    deliverable_name: str
    deliverable_type: str
    type: MessageType = field(default=MessageType.DELIVERABLE_STARTED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "deliverable_id": self.deliverable_id,
            "deliverable_name": self.deliverable_name,
            "deliverable_type": self.deliverable_type,
        }


@dataclass
class DeliverableCompletedMessage(BaseMessage):
    deliverable_id: str
    status: str
    output_path: Optional[str] = None
    error: Optional[str] = None
    type: MessageType = field(default=MessageType.DELIVERABLE_COMPLETED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "deliverable_id": self.deliverable_id,
            "status": self.status,
            "output_path": self.output_path,
            "error": self.error,
        }


@dataclass
class SectionStartedMessage(BaseMessage):
    section_id: str
    section_title: str
    section_type: str
    type: MessageType = field(default=MessageType.SECTION_STARTED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "section_type": self.section_type,
        }


@dataclass
class SectionCompletedMessage(BaseMessage):
    section_id: str
    status: str
    content_preview: str = ""
    files_created: List[str] = field(default_factory=list)
    error: Optional[str] = None
    type: MessageType = field(default=MessageType.SECTION_COMPLETED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "section_id": self.section_id,
            "status": self.status,
            "content_preview": self.content_preview,
            "files_created": self.files_created,
            "error": self.error,
        }


@dataclass
class ProjectCompletedMessage(BaseMessage):
    task: str
    status: str
    deliverables_completed: int
    deliverables_failed: int
    summary: str
    type: MessageType = field(default=MessageType.PROJECT_COMPLETED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "task": self.task,
            "status": self.status,
            "deliverables_completed": self.deliverables_completed,
            "deliverables_failed": self.deliverables_failed,
            "summary": self.summary,
        }


def parse_client_message(data: Dict[str, Any]) -> Optional[BaseMessage]:
    msg_type = data.get("type")
    
    if msg_type == "chat":
        return ChatMessage(content=data.get("content", ""))
    elif msg_type == "suggestion":
        return SuggestionMessage(content=data.get("content", ""))
    elif msg_type == "request_plan":
        return RequestPlanMessage(content=data.get("content", ""))
    elif msg_type == "approve_plan":
        return ApprovePlanMessage(type=MessageType.APPROVE_PLAN)
    elif msg_type == "update_plan":
        return UpdatePlanMessage(modifications=data.get("modifications", {}))
    elif msg_type == "interrupt":
        return BaseMessage(type=MessageType.INTERRUPT)
    elif msg_type == "pause_execution":
        return BaseMessage(type=MessageType.PAUSE_EXECUTION)
    elif msg_type == "resume_execution":
        return BaseMessage(type=MessageType.RESUME_EXECUTION)
    
    return None
