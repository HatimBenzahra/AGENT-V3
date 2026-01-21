from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import yaml


class DeliverableType(Enum):
    REPORT = "report"
    CODE = "code"
    APP = "app"
    PRESENTATION = "presentation"
    ARCHIVE = "archive"
    DATA = "data"
    WEBSITE = "website"


class SectionType(Enum):
    TEXT = "text"
    CHART = "chart"
    TABLE = "table"
    CODE = "code"
    IMAGE = "image"
    LIST = "list"
    COVER = "cover"
    TOC = "toc"  # Table of contents


class OutputFormat(Enum):
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MD = "markdown"
    ZIP = "zip"
    FOLDER = "folder"
    PPTX = "pptx"
    JSON = "json"
    CSV = "csv"


@dataclass
class EditableField:
    name: str
    field_type: str  # "text", "number", "select", "multiline"
    default: Any = None
    options: List[str] = field(default_factory=list)  # For select type
    required: bool = True


@dataclass
class Section:
    id: str
    title: str
    section_type: SectionType
    description: str = ""
    subsections: List["Section"] = field(default_factory=list)
    editable_fields: List[EditableField] = field(default_factory=list)
    optional: bool = False
    order: int = 0
    content_hint: str = ""  # LLM hint for content generation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "section_type": self.section_type.value,
            "description": self.description,
            "subsections": [s.to_dict() for s in self.subsections],
            "editable_fields": [
                {"name": f.name, "field_type": f.field_type, "default": f.default, 
                 "options": f.options, "required": f.required}
                for f in self.editable_fields
            ],
            "optional": self.optional,
            "order": self.order,
            "content_hint": self.content_hint,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Section":
        subsections = [cls.from_dict(s) for s in data.get("subsections", [])]
        editable_fields = [
            EditableField(
                name=f["name"],
                field_type=f["field_type"],
                default=f.get("default"),
                options=f.get("options", []),
                required=f.get("required", True),
            )
            for f in data.get("editable_fields", [])
        ]
        return cls(
            id=data["id"],
            title=data["title"],
            section_type=SectionType(data["section_type"]),
            description=data.get("description", ""),
            subsections=subsections,
            editable_fields=editable_fields,
            optional=data.get("optional", False),
            order=data.get("order", 0),
            content_hint=data.get("content_hint", ""),
        )


@dataclass
class Deliverable:
    id: str
    deliverable_type: DeliverableType
    name: str
    sections: List[Section]
    output_format: OutputFormat
    depends_on: List[str] = field(default_factory=list)
    tools_required: List[str] = field(default_factory=list)
    quality_gates: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "deliverable_type": self.deliverable_type.value,
            "name": self.name,
            "sections": [s.to_dict() for s in self.sections],
            "output_format": self.output_format.value,
            "depends_on": self.depends_on,
            "tools_required": self.tools_required,
            "quality_gates": self.quality_gates,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Deliverable":
        sections = [Section.from_dict(s) for s in data.get("sections", [])]
        return cls(
            id=data["id"],
            deliverable_type=DeliverableType(data["deliverable_type"]),
            name=data["name"],
            sections=sections,
            output_format=OutputFormat(data["output_format"]),
            depends_on=data.get("depends_on", []),
            tools_required=data.get("tools_required", []),
            quality_gates=data.get("quality_gates", []),
        )


@dataclass
class ProjectPlan:
    task: str
    title: str
    deliverables: List[Deliverable]
    execution_order: List[str] = field(default_factory=list)
    cross_references: Dict[str, List[str]] = field(default_factory=dict)
    user_modified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "title": self.title,
            "deliverables": [d.to_dict() for d in self.deliverables],
            "execution_order": self.execution_order,
            "cross_references": self.cross_references,
            "user_modified": self.user_modified,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectPlan":
        deliverables = [Deliverable.from_dict(d) for d in data.get("deliverables", [])]
        return cls(
            task=data["task"],
            title=data["title"],
            deliverables=deliverables,
            execution_order=data.get("execution_order", []),
            cross_references=data.get("cross_references", {}),
            user_modified=data.get("user_modified", False),
        )
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"**Tâche originale**: {self.task}",
            "",
            f"**Livrables**: {len(self.deliverables)}",
            "",
            "---",
            "",
        ]
        
        for i, deliverable in enumerate(self.deliverables, 1):
            emoji = {
                DeliverableType.REPORT: "📄",
                DeliverableType.CODE: "💻",
                DeliverableType.APP: "🖥️",
                DeliverableType.PRESENTATION: "📊",
                DeliverableType.ARCHIVE: "📦",
                DeliverableType.DATA: "📈",
                DeliverableType.WEBSITE: "🌐",
            }.get(deliverable.deliverable_type, "📁")
            
            lines.append(f"## {emoji} Livrable {i}: {deliverable.name}")
            lines.append(f"**Type**: {deliverable.deliverable_type.value}")
            lines.append(f"**Format de sortie**: {deliverable.output_format.value}")
            
            if deliverable.depends_on:
                lines.append(f"**Dépend de**: {', '.join(deliverable.depends_on)}")
            
            lines.append("")
            lines.append("### Structure")
            lines.append("")
            
            for section in deliverable.sections:
                self._render_section_markdown(section, lines, level=0)
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        if self.execution_order:
            lines.append("## Ordre d'exécution")
            lines.append("")
            for i, deliverable_id in enumerate(self.execution_order, 1):
                lines.append(f"{i}. {deliverable_id}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _render_section_markdown(self, section: Section, lines: List[str], level: int):
        indent = "  " * level
        optional_mark = " *(optionnel)*" if section.optional else ""
        
        type_emoji = {
            SectionType.TEXT: "📝",
            SectionType.CHART: "📊",
            SectionType.TABLE: "📋",
            SectionType.CODE: "💻",
            SectionType.IMAGE: "🖼️",
            SectionType.LIST: "📌",
            SectionType.COVER: "📕",
            SectionType.TOC: "📑",
        }.get(section.section_type, "•")
        
        lines.append(f"{indent}- {type_emoji} **{section.title}**{optional_mark}")
        
        if section.description:
            lines.append(f"{indent}  {section.description}")
        
        for subsection in section.subsections:
            self._render_section_markdown(subsection, lines, level + 1)


@dataclass
class Playbook:
    id: str
    name: str
    deliverable_type: DeliverableType
    triggers: List[str]  # Keywords that trigger this playbook
    default_sections: List[Section]
    tools_allowed: List[str]
    quality_gates: List[str]
    output_formats: List[OutputFormat]
    examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "deliverable_type": self.deliverable_type.value,
            "triggers": self.triggers,
            "default_sections": [s.to_dict() for s in self.default_sections],
            "tools_allowed": self.tools_allowed,
            "quality_gates": self.quality_gates,
            "output_formats": [f.value for f in self.output_formats],
            "examples": self.examples,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Playbook":
        default_sections = [Section.from_dict(s) for s in data.get("default_sections", [])]
        output_formats = [OutputFormat(f) for f in data.get("output_formats", ["pdf"])]
        return cls(
            id=data["id"],
            name=data["name"],
            deliverable_type=DeliverableType(data["deliverable_type"]),
            triggers=data.get("triggers", []),
            default_sections=default_sections,
            tools_allowed=data.get("tools_allowed", []),
            quality_gates=data.get("quality_gates", []),
            output_formats=output_formats,
            examples=data.get("examples", []),
        )
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Playbook":
        data = yaml.safe_load(yaml_content)
        return cls.from_dict(data)
    
    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), allow_unicode=True, default_flow_style=False)
