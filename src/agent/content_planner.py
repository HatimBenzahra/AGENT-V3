import json
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.models.llm_client import LLMClient
from src.agent.playbooks.schema import (
    Section, Deliverable, ProjectPlan, Playbook,
    DeliverableType, SectionType, OutputFormat
)
from src.agent.playbooks.store import get_playbook_store
from src.agent.project_analyzer import (
    ProjectAnalyzer, AnalysisResult, DetectedDeliverable, DetectedDependency
)


CONTENT_PLANNING_PROMPT = """Tu es un expert en structuration de contenu. Ton rôle est de créer un PLAN ÉDITORIAL détaillé (pas technique) pour un projet.

RÈGLES CRITIQUES:
1. Le plan doit être ÉDITORIAL, pas technique. L'utilisateur veut voir la STRUCTURE DU CONTENU, pas les étapes de création.
2. Chaque section doit être suffisamment détaillée pour que l'utilisateur puisse la modifier.
3. Pour un rapport/document: inclure toutes les sections et sous-sections avec leurs titres.
4. Pour du code: inclure l'arborescence des fichiers avec descriptions.
5. Pour une app: inclure les pages, composants, et structure.

PLAYBOOK DE RÉFÉRENCE (template par défaut):
{playbook_content}

TÂCHE À PLANIFIER:
{task}

LIVRABLES DÉTECTÉS:
{deliverables}

DÉPENDANCES:
{dependencies}

Tu dois générer un plan JSON avec cette structure EXACTE:
{{
    "title": "Titre du projet",
    "deliverables": [
        {{
            "id": "deliverable_1",
            "deliverable_type": "report|code|app|presentation|archive",
            "name": "Nom du livrable",
            "output_format": "pdf|folder|zip|pptx",
            "depends_on": ["ids des dépendances"],
            "sections": [
                {{
                    "id": "section_id",
                    "title": "Titre de la section",
                    "section_type": "text|chart|table|code|image|list|cover|toc",
                    "description": "Description courte",
                    "optional": false,
                    "content_hint": "Indications pour le contenu",
                    "subsections": [...]
                }}
            ]
        }}
    ],
    "execution_order": ["deliverable_1", "deliverable_2"]
}}

IMPORTANT:
- Génère UNIQUEMENT du JSON valide, sans texte avant ou après.
- Les sections doivent être SPÉCIFIQUES au sujet demandé, pas génériques.
- Adapte la structure du playbook au contexte spécifique de la tâche.
"""


class ContentPlanner:
    
    def __init__(self):
        self.llm = LLMClient()
        self.analyzer = ProjectAnalyzer()
        self.playbook_store = get_playbook_store()
    
    async def create_plan(self, task: str) -> ProjectPlan:
        analysis = self.analyzer.analyze(task)
        
        if not analysis.needs_planning and len(analysis.deliverables) <= 1:
            return self._create_simple_plan(task, analysis)
        
        return await self._create_llm_plan(task, analysis)
    
    def _create_simple_plan(self, task: str, analysis: AnalysisResult) -> ProjectPlan:
        if not analysis.deliverables:
            return ProjectPlan(
                task=task,
                title="Tâche simple",
                deliverables=[],
                execution_order=[],
            )
        
        detected = analysis.deliverables[0]
        playbook = detected.playbook or self.playbook_store.find_best_match(task)
        
        if playbook:
            sections = [Section.from_dict(s.to_dict()) for s in playbook.default_sections]
        else:
            sections = self._get_default_sections(detected.deliverable_type)
        
        deliverable = Deliverable(
            id="deliverable_1",
            deliverable_type=detected.deliverable_type,
            name=detected.name,
            sections=sections,
            output_format=detected.output_format or OutputFormat.PDF,
            depends_on=[],
            tools_required=playbook.tools_allowed if playbook else [],
            quality_gates=playbook.quality_gates if playbook else [],
        )
        
        return ProjectPlan(
            task=task,
            title=detected.name,
            deliverables=[deliverable],
            execution_order=["deliverable_1"],
        )
    
    async def _create_llm_plan(self, task: str, analysis: AnalysisResult) -> ProjectPlan:
        primary_playbook = None
        if analysis.deliverables:
            primary_playbook = analysis.deliverables[0].playbook
        
        if not primary_playbook:
            primary_playbook = self.playbook_store.find_best_match(task)
        
        playbook_content = "Aucun playbook spécifique trouvé. Utilise une structure standard."
        if primary_playbook:
            playbook_content = json.dumps(primary_playbook.to_dict(), indent=2, ensure_ascii=False)
        
        deliverables_str = "\n".join([
            f"- {d.name} ({d.deliverable_type.value}): {d.description}"
            for d in analysis.deliverables
        ]) or "Aucun livrable spécifique détecté"
        
        dependencies_str = "\n".join([
            f"- {d.from_deliverable} → {d.to_deliverable}: {d.reason}"
            for d in analysis.dependencies
        ]) or "Aucune dépendance détectée"
        
        prompt = CONTENT_PLANNING_PROMPT.format(
            playbook_content=playbook_content,
            task=task,
            deliverables=deliverables_str,
            dependencies=dependencies_str,
        )
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Génère le plan éditorial pour: {task}"},
        ]
        
        response = await self.llm.chat_completion(messages)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                plan_data = json.loads(json_match.group())
                return self._parse_llm_plan(task, plan_data, analysis)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ContentPlanner] Failed to parse LLM response: {e}")
        
        return self._create_fallback_plan(task, analysis)
    
    def _parse_llm_plan(
        self, 
        task: str, 
        data: Dict[str, Any], 
        analysis: AnalysisResult
    ) -> ProjectPlan:
        deliverables = []
        
        for d_data in data.get("deliverables", []):
            sections = self._parse_sections(d_data.get("sections", []))
            
            try:
                dtype = DeliverableType(d_data.get("deliverable_type", "report"))
            except ValueError:
                dtype = DeliverableType.REPORT
            
            try:
                output_format = OutputFormat(d_data.get("output_format", "pdf"))
            except ValueError:
                output_format = OutputFormat.PDF
            
            deliverable = Deliverable(
                id=d_data.get("id", f"deliverable_{len(deliverables)+1}"),
                deliverable_type=dtype,
                name=d_data.get("name", "Livrable"),
                sections=sections,
                output_format=output_format,
                depends_on=d_data.get("depends_on", []),
                tools_required=d_data.get("tools_required", []),
                quality_gates=d_data.get("quality_gates", []),
            )
            deliverables.append(deliverable)
        
        execution_order = data.get("execution_order", [d.id for d in deliverables])
        
        return ProjectPlan(
            task=task,
            title=data.get("title", "Projet"),
            deliverables=deliverables,
            execution_order=execution_order,
        )
    
    def _parse_sections(self, sections_data: List[Dict]) -> List[Section]:
        sections = []
        
        for s_data in sections_data:
            try:
                section_type = SectionType(s_data.get("section_type", "text"))
            except ValueError:
                section_type = SectionType.TEXT
            
            subsections = self._parse_sections(s_data.get("subsections", []))
            
            section = Section(
                id=s_data.get("id", f"section_{len(sections)+1}"),
                title=s_data.get("title", "Section"),
                section_type=section_type,
                description=s_data.get("description", ""),
                subsections=subsections,
                optional=s_data.get("optional", False),
                order=s_data.get("order", len(sections)),
                content_hint=s_data.get("content_hint", ""),
            )
            sections.append(section)
        
        return sections
    
    def _create_fallback_plan(self, task: str, analysis: AnalysisResult) -> ProjectPlan:
        deliverables = []
        
        for i, detected in enumerate(analysis.deliverables):
            playbook = detected.playbook or self.playbook_store.find_best_match(task)
            
            if playbook:
                sections = [Section.from_dict(s.to_dict()) for s in playbook.default_sections]
            else:
                sections = self._get_default_sections(detected.deliverable_type)
            
            deliverable = Deliverable(
                id=f"deliverable_{i+1}",
                deliverable_type=detected.deliverable_type,
                name=detected.name,
                sections=sections,
                output_format=detected.output_format or OutputFormat.PDF,
                depends_on=[],
                tools_required=[],
                quality_gates=[],
            )
            deliverables.append(deliverable)
        
        for dep in analysis.dependencies:
            for d in deliverables:
                if d.name == dep.to_deliverable:
                    from_id = next(
                        (dd.id for dd in deliverables if dd.name == dep.from_deliverable),
                        None
                    )
                    if from_id and from_id not in d.depends_on:
                        d.depends_on.append(from_id)
        
        return ProjectPlan(
            task=task,
            title=analysis.deliverables[0].name if analysis.deliverables else "Projet",
            deliverables=deliverables,
            execution_order=analysis.execution_order,
        )
    
    def _get_default_sections(self, dtype: DeliverableType) -> List[Section]:
        default_sections = {
            DeliverableType.REPORT: [
                Section(id="cover", title="Page de garde", section_type=SectionType.COVER, order=1),
                Section(id="summary", title="Résumé", section_type=SectionType.TEXT, order=2),
                Section(id="intro", title="Introduction", section_type=SectionType.TEXT, order=3),
                Section(id="content", title="Contenu principal", section_type=SectionType.TEXT, order=4),
                Section(id="conclusion", title="Conclusion", section_type=SectionType.TEXT, order=5),
            ],
            DeliverableType.CODE: [
                Section(id="structure", title="Structure du projet", section_type=SectionType.CODE, order=1),
                Section(id="main", title="Code principal", section_type=SectionType.CODE, order=2),
                Section(id="tests", title="Tests", section_type=SectionType.CODE, optional=True, order=3),
            ],
            DeliverableType.APP: [
                Section(id="frontend", title="Interface", section_type=SectionType.CODE, order=1),
                Section(id="backend", title="Backend", section_type=SectionType.CODE, optional=True, order=2),
                Section(id="config", title="Configuration", section_type=SectionType.CODE, order=3),
            ],
            DeliverableType.PRESENTATION: [
                Section(id="title", title="Slide de titre", section_type=SectionType.COVER, order=1),
                Section(id="agenda", title="Agenda", section_type=SectionType.LIST, order=2),
                Section(id="content", title="Contenu", section_type=SectionType.TEXT, order=3),
                Section(id="conclusion", title="Conclusion", section_type=SectionType.TEXT, order=4),
            ],
        }
        
        return default_sections.get(dtype, [
            Section(id="main", title="Contenu principal", section_type=SectionType.TEXT, order=1)
        ])
    
    async def update_plan(self, plan: ProjectPlan, modifications: Dict[str, Any]) -> ProjectPlan:
        if "deliverables" in modifications:
            for mod_d in modifications["deliverables"]:
                for d in plan.deliverables:
                    if d.id == mod_d.get("id"):
                        if "sections" in mod_d:
                            d.sections = self._parse_sections(mod_d["sections"])
                        if "name" in mod_d:
                            d.name = mod_d["name"]
                        if "output_format" in mod_d:
                            try:
                                d.output_format = OutputFormat(mod_d["output_format"])
                            except ValueError:
                                pass
        
        if "execution_order" in modifications:
            plan.execution_order = modifications["execution_order"]
        
        if "title" in modifications:
            plan.title = modifications["title"]
        
        plan.user_modified = True
        
        return plan


async def create_content_plan(task: str) -> ProjectPlan:
    planner = ContentPlanner()
    return await planner.create_plan(task)
