from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class RecipeCategory(Enum):
    DOCUMENTS = "documents"
    CODE_C_CPP = "code_c_cpp"
    CODE_PYTHON = "code_python"
    WEB_FRONTEND = "web_frontend"
    WEB_BACKEND = "web_backend"
    DEVOPS = "devops"
    SYSTEM = "system"
    DATA = "data"


@dataclass
class Recipe:
    title: str
    category: RecipeCategory
    question: str
    answer: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    difficulty: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category.value,
            "question": self.question,
            "answer": self.answer,
            "tags": self.tags,
            "examples": self.examples,
            "related": self.related,
            "tools_used": self.tools_used,
            "difficulty": self.difficulty,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recipe":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            title=data["title"],
            category=RecipeCategory(data.get("category", "system")),
            question=data["question"],
            answer=data["answer"],
            tags=data.get("tags", []),
            examples=data.get("examples", []),
            related=data.get("related", []),
            tools_used=data.get("tools_used", []),
            difficulty=data.get("difficulty", "medium"),
        )
    
    def to_searchable_text(self) -> str:
        parts = [
            self.title,
            self.question,
            self.answer,
            " ".join(self.tags),
            " ".join(self.examples),
        ]
        return " ".join(parts)
