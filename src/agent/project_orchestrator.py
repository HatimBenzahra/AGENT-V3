import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from src.agent.playbooks.schema import (
    ProjectPlan, Deliverable, Section, DeliverableType, OutputFormat
)
from src.agent.content_planner import ContentPlanner
from src.agent.state import AgentState
from src.models.llm_client import LLMClient
from src.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from fastapi import WebSocket
    from src.session.conversation_context import ConversationContext


class ProjectStatus(Enum):
    ANALYZING = "analyzing"
    PLANNING = "planning"
    PENDING_APPROVAL = "pending_approval"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class DeliverableStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SectionStatus(Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SectionResult:
    section_id: str
    status: SectionStatus
    content: str = ""
    files_created: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class DeliverableResult:
    deliverable_id: str
    status: DeliverableStatus
    section_results: List[SectionResult] = field(default_factory=list)
    output_path: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "deliverable_id": self.deliverable_id,
            "status": self.status.value,
            "section_results": [
                {
                    "section_id": sr.section_id,
                    "status": sr.status.value,
                    "content": sr.content[:200] + "..." if len(sr.content) > 200 else sr.content,
                    "files_created": sr.files_created,
                    "error": sr.error,
                }
                for sr in self.section_results
            ],
            "output_path": self.output_path,
            "error": self.error,
        }


@dataclass
class ProjectResult:
    task: str
    plan: ProjectPlan
    status: ProjectStatus
    deliverable_results: List[DeliverableResult] = field(default_factory=list)
    final_summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "plan": self.plan.to_dict(),
            "status": self.status.value,
            "deliverable_results": [dr.to_dict() for dr in self.deliverable_results],
            "final_summary": self.final_summary,
        }


class ProjectOrchestrator:
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        conversation_context: Optional["ConversationContext"] = None,
        websocket: Optional["WebSocket"] = None,
    ):
        self.tools = tool_registry
        self.conversation_context = conversation_context
        self.websocket = websocket
        
        self.content_planner = ContentPlanner()
        self.llm = LLMClient()
        
        self.current_plan: Optional[ProjectPlan] = None
        self.current_status: ProjectStatus = ProjectStatus.ANALYZING
        self.plan_approved: bool = False
        self.should_pause: bool = False
        
        self.on_plan_created: Optional[Callable[[ProjectPlan], None]] = None
        self.on_deliverable_started: Optional[Callable[[Deliverable], None]] = None
        self.on_deliverable_completed: Optional[Callable[[DeliverableResult], None]] = None
        self.on_section_started: Optional[Callable[[Section], None]] = None
        self.on_section_completed: Optional[Callable[[SectionResult], None]] = None
    
    async def _notify(self, msg_type: str, **data):
        if self.websocket:
            try:
                await self.websocket.send_json({"type": msg_type, **data})
            except Exception:
                pass
    
    async def analyze_and_plan(self, task: str) -> ProjectPlan:
        self.current_status = ProjectStatus.ANALYZING
        await self._notify("project_analyzing", task=task)
        
        self.current_status = ProjectStatus.PLANNING
        await self._notify("project_planning", task=task)
        
        plan = await self.content_planner.create_plan(task)
        self.current_plan = plan
        
        await self._notify("project_plan_created", plan=plan.to_dict())
        
        if self.on_plan_created:
            self.on_plan_created(plan)
        
        self.current_status = ProjectStatus.PENDING_APPROVAL
        await self._notify("project_pending_approval", plan_markdown=plan.to_markdown())
        
        return plan
    
    async def update_plan(self, modifications: Dict[str, Any]) -> ProjectPlan:
        if self.current_plan is None:
            raise ValueError("No plan to update")
        
        updated_plan = await self.content_planner.update_plan(
            self.current_plan, modifications
        )
        self.current_plan = updated_plan
        
        await self._notify("project_plan_updated", plan=updated_plan.to_dict())
        
        return updated_plan
    
    def approve_plan(self):
        self.plan_approved = True
        self.current_status = ProjectStatus.EXECUTING
    
    def pause_execution(self):
        self.should_pause = True
    
    def resume_execution(self):
        self.should_pause = False
    
    async def execute(self, task: str, auto_approve: bool = False) -> ProjectResult:
        if not self.current_plan:
            await self.analyze_and_plan(task)
        
        plan = self.current_plan
        if plan is None:
            raise ValueError("Failed to create plan")
        
        if not auto_approve and not self.plan_approved:
            return ProjectResult(
                task=task,
                plan=plan,
                status=ProjectStatus.PENDING_APPROVAL,
                final_summary="En attente d'approbation du plan",
            )
        
        self.current_status = ProjectStatus.EXECUTING
        await self._notify("project_execution_started", task=task)
        
        result = ProjectResult(
            task=task,
            plan=plan,
            status=ProjectStatus.EXECUTING,
        )
        
        for deliverable_id in plan.execution_order:
            if self.should_pause:
                self.current_status = ProjectStatus.PAUSED
                await self._notify("project_paused")
                while self.should_pause:
                    await asyncio.sleep(0.5)
                self.current_status = ProjectStatus.EXECUTING
                await self._notify("project_resumed")
            
            deliverable = next(
                (d for d in plan.deliverables if d.id == deliverable_id),
                None
            )
            
            if not deliverable:
                continue
            
            deps_satisfied = self._check_dependencies(deliverable, result.deliverable_results)
            if not deps_satisfied:
                result.deliverable_results.append(DeliverableResult(
                    deliverable_id=deliverable_id,
                    status=DeliverableStatus.SKIPPED,
                    error="Dépendances non satisfaites",
                ))
                continue
            
            deliverable_result = await self._execute_deliverable(deliverable, result)
            result.deliverable_results.append(deliverable_result)
            
            if deliverable_result.status == DeliverableStatus.FAILED:
                result.status = ProjectStatus.FAILED
                result.final_summary = f"Échec sur le livrable: {deliverable.name}"
                await self._notify("project_failed", error=result.final_summary)
                return result
        
        result.status = ProjectStatus.COMPLETED
        result.final_summary = self._generate_summary(result)
        
        await self._notify("project_completed", result=result.to_dict())
        
        return result
    
    def _check_dependencies(
        self, 
        deliverable: Deliverable, 
        results: List[DeliverableResult]
    ) -> bool:
        for dep_id in deliverable.depends_on:
            dep_result = next((r for r in results if r.deliverable_id == dep_id), None)
            if not dep_result or dep_result.status != DeliverableStatus.COMPLETED:
                return False
        return True
    
    async def _execute_deliverable(
        self, 
        deliverable: Deliverable,
        project_result: ProjectResult,
    ) -> DeliverableResult:
        await self._notify("deliverable_started", deliverable=deliverable.to_dict())
        
        if self.on_deliverable_started:
            self.on_deliverable_started(deliverable)
        
        result = DeliverableResult(
            deliverable_id=deliverable.id,
            status=DeliverableStatus.IN_PROGRESS,
        )
        
        context = self._build_deliverable_context(deliverable, project_result)
        
        for section in deliverable.sections:
            if self.should_pause:
                await asyncio.sleep(0.5)
                continue
            
            section_result = await self._execute_section(
                section, deliverable, context
            )
            result.section_results.append(section_result)
            
            context["completed_sections"].append({
                "id": section.id,
                "title": section.title,
                "content": section_result.content[:500],
            })
            
            if section_result.status == SectionStatus.FAILED and not section.optional:
                result.status = DeliverableStatus.FAILED
                result.error = f"Section obligatoire échouée: {section.title}"
                return result
        
        output_path = await self._finalize_deliverable(deliverable, result)
        result.output_path = output_path
        result.status = DeliverableStatus.COMPLETED
        
        await self._notify("deliverable_completed", result=result.to_dict())
        
        if self.on_deliverable_completed:
            self.on_deliverable_completed(result)
        
        return result
    
    def _build_deliverable_context(
        self, 
        deliverable: Deliverable,
        project_result: ProjectResult,
    ) -> Dict[str, Any]:
        previous_deliverables = []
        plan_deliverables = self.current_plan.deliverables if self.current_plan else []
        for dr in project_result.deliverable_results:
            if dr.status == DeliverableStatus.COMPLETED:
                d = next(
                    (d for d in plan_deliverables if d.id == dr.deliverable_id),
                    None
                )
                if d:
                    previous_deliverables.append({
                        "id": d.id,
                        "name": d.name,
                        "type": d.deliverable_type.value,
                        "output_path": dr.output_path,
                        "key_content": self._extract_key_content(dr),
                    })
        
        return {
            "task": project_result.task,
            "deliverable": deliverable,
            "previous_deliverables": previous_deliverables,
            "completed_sections": [],
        }
    
    def _extract_key_content(self, deliverable_result: DeliverableResult) -> str:
        key_parts = []
        for sr in deliverable_result.section_results[:3]:
            if sr.content:
                key_parts.append(f"[{sr.section_id}]: {sr.content[:200]}")
        return "\n".join(key_parts)
    
    async def _execute_section(
        self,
        section: Section,
        deliverable: Deliverable,
        context: Dict[str, Any],
    ) -> SectionResult:
        await self._notify("section_started", section=section.to_dict())
        
        if self.on_section_started:
            self.on_section_started(section)
        
        prompt = self._build_section_prompt(section, deliverable, context)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Génère le contenu pour la section: {section.title}"},
        ]
        
        try:
            content = await self.llm.chat_completion(messages)
            
            files_created = []
            if section.section_type.value == "code":
                files_created = await self._create_code_files(content, deliverable)
            
            result = SectionResult(
                section_id=section.id,
                status=SectionStatus.COMPLETED,
                content=content,
                files_created=files_created,
            )
            
        except Exception as e:
            result = SectionResult(
                section_id=section.id,
                status=SectionStatus.FAILED,
                error=str(e),
            )
        
        await self._notify("section_completed", result={
            "section_id": result.section_id,
            "status": result.status.value,
        })
        
        if self.on_section_completed:
            self.on_section_completed(result)
        
        return result
    
    def _build_section_prompt(
        self,
        section: Section,
        deliverable: Deliverable,
        context: Dict[str, Any],
    ) -> str:
        previous_context = ""
        if context["previous_deliverables"]:
            previous_context = "LIVRABLES PRÉCÉDENTS:\n"
            for pd in context["previous_deliverables"]:
                previous_context += f"- {pd['name']} ({pd['type']})\n{pd['key_content']}\n\n"
        
        completed_sections = ""
        if context["completed_sections"]:
            completed_sections = "SECTIONS DÉJÀ COMPLÉTÉES:\n"
            for cs in context["completed_sections"][-3:]:
                completed_sections += f"- {cs['title']}: {cs['content'][:100]}...\n"
        
        return f"""Tu dois générer le contenu pour une section d'un {deliverable.deliverable_type.value}.

TÂCHE GLOBALE: {context['task']}

LIVRABLE ACTUEL: {deliverable.name}
TYPE: {deliverable.deliverable_type.value}
FORMAT DE SORTIE: {deliverable.output_format.value}

{previous_context}

{completed_sections}

SECTION À GÉNÉRER:
- Titre: {section.title}
- Type: {section.section_type.value}
- Description: {section.description}
- Indications: {section.content_hint}

RÈGLES:
- Génère du contenu de qualité professionnelle
- Adapte le style au type de livrable
- Si c'est du code, génère du code fonctionnel et bien commenté
- Si c'est du texte, génère du contenu structuré et informatif
- Utilise les informations des livrables précédents si pertinent
"""
    
    async def _create_code_files(self, content: str, deliverable: Deliverable) -> List[str]:
        files_created = []
        
        code_blocks = self._extract_code_blocks(content)
        
        for filename, code in code_blocks:
            write_tool = self.tools.get_tool("write_file")
            if write_tool:
                try:
                    await write_tool.execute(file_path=filename, content=code)
                    files_created.append(filename)
                except Exception as e:
                    print(f"[ProjectOrchestrator] Failed to create file {filename}: {e}")
        
        return files_created
    
    def _extract_code_blocks(self, content: str) -> List[tuple]:
        import re
        
        pattern = r'```(\w+)?\s*(?:#\s*(\S+))?\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        blocks = []
        for i, (lang, filename, code) in enumerate(matches):
            if not filename:
                ext = {"python": ".py", "javascript": ".js", "c": ".c", "cpp": ".cpp"}.get(lang, ".txt")
                filename = f"file_{i+1}{ext}"
            blocks.append((filename, code.strip()))
        
        return blocks
    
    async def _finalize_deliverable(
        self, 
        deliverable: Deliverable, 
        result: DeliverableResult
    ) -> Optional[str]:
        if deliverable.output_format == OutputFormat.PDF:
            pdf_tool = self.tools.get_tool("create_pdf")
            if pdf_tool:
                content = "\n\n".join([
                    f"# {sr.section_id}\n{sr.content}"
                    for sr in result.section_results
                    if sr.content
                ])
                try:
                    output = await pdf_tool.execute(
                        content=content,
                        filename=f"{deliverable.name.replace(' ', '_')}.pdf"
                    )
                    return output
                except Exception as e:
                    print(f"[ProjectOrchestrator] Failed to create PDF: {e}")
        
        elif deliverable.output_format == OutputFormat.ZIP:
            terminal_tool = self.tools.get_tool("execute_command")
            if terminal_tool:
                files = []
                for sr in result.section_results:
                    files.extend(sr.files_created)
                
                if files:
                    try:
                        zip_name = f"{deliverable.name.replace(' ', '_')}.zip"
                        files_str = " ".join(files)
                        await terminal_tool.execute(command=f"zip -r {zip_name} {files_str}")
                        return zip_name
                    except Exception as e:
                        print(f"[ProjectOrchestrator] Failed to create ZIP: {e}")
        
        return None
    
    def _generate_summary(self, result: ProjectResult) -> str:
        completed = [dr for dr in result.deliverable_results if dr.status == DeliverableStatus.COMPLETED]
        failed = [dr for dr in result.deliverable_results if dr.status == DeliverableStatus.FAILED]
        
        lines = [
            f"# Résumé du projet: {result.plan.title}",
            "",
            f"**Tâche**: {result.task}",
            f"**Statut**: {'Terminé' if result.status == ProjectStatus.COMPLETED else 'Échoué'}",
            "",
            "## Livrables complétés",
        ]
        
        for dr in completed:
            d = next((d for d in result.plan.deliverables if d.id == dr.deliverable_id), None)
            if d:
                lines.append(f"- **{d.name}** ({d.deliverable_type.value})")
                if dr.output_path:
                    lines.append(f"  - Fichier: {dr.output_path}")
        
        if failed:
            lines.append("")
            lines.append("## Livrables échoués")
            for dr in failed:
                d = next((d for d in result.plan.deliverables if d.id == dr.deliverable_id), None)
                if d:
                    lines.append(f"- **{d.name}**: {dr.error}")
        
        return "\n".join(lines)
