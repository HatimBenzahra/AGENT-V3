import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

from src.agent.playbooks.schema import DeliverableType, OutputFormat
from src.agent.playbooks.store import get_playbook_store, Playbook


class DependencyType(Enum):
    CONTENT_REFERENCE = "content_reference"  # Livrable B référence contenu de A
    OUTPUT_INPUT = "output_input"  # Output de A est input de B
    SEQUENTIAL = "sequential"  # B doit être fait après A (ordre logique)


@dataclass
class DetectedDeliverable:
    deliverable_type: DeliverableType
    name: str
    description: str
    keywords_matched: List[str]
    confidence: float  # 0-1
    playbook: Optional[Playbook] = None
    output_format: Optional[OutputFormat] = None


@dataclass
class DetectedDependency:
    from_deliverable: str
    to_deliverable: str
    dependency_type: DependencyType
    reason: str


@dataclass
class AnalysisResult:
    original_task: str
    is_complex: bool
    deliverables: List[DetectedDeliverable]
    dependencies: List[DetectedDependency]
    execution_order: List[str]
    needs_planning: bool
    complexity_score: float  # 0-1


DELIVERABLE_PATTERNS: Dict[DeliverableType, Dict] = {
    DeliverableType.REPORT: {
        "keywords": [
            "rapport", "report", "document", "pdf", "article", "étude", "analyse",
            "synthèse", "mémoire", "dossier", "rédige", "écris", "rédiger", "écrire"
        ],
        "patterns": [
            r"(fais|crée|génère|rédige).*(rapport|document|article|étude|pdf)",
            r"(rapport|document|étude).*(sur|à propos|concernant)",
        ],
        "output_formats": [OutputFormat.PDF, OutputFormat.MD, OutputFormat.DOCX],
    },
    DeliverableType.CODE: {
        "keywords": [
            "code", "script", "programme", "program", "implémente", "implement",
            "fonction", "function", "algorithme", "algorithm", "développe", "develop",
            "coding", "coder", "programmer"
        ],
        "patterns": [
            r"(implémente|développe|code|écris).*(en|avec)\s*(python|javascript|c\+\+|c|java|go|rust)",
            r"(crée|fais).*(script|programme|fonction|algorithme)",
        ],
        "output_formats": [OutputFormat.FOLDER, OutputFormat.ZIP],
    },
    DeliverableType.APP: {
        "keywords": [
            "application", "app", "webapp", "website", "site", "frontend", "backend",
            "interface", "dashboard", "crud", "api"
        ],
        "patterns": [
            r"(crée|développe|fais).*(application|app|site|webapp|dashboard)",
            r"(application|app).*(avec|en|utilisant)",
        ],
        "output_formats": [OutputFormat.FOLDER, OutputFormat.ZIP],
    },
    DeliverableType.PRESENTATION: {
        "keywords": [
            "présentation", "presentation", "slides", "powerpoint", "pptx",
            "diaporama", "pitch", "keynote"
        ],
        "patterns": [
            r"(crée|fais|prépare).*(présentation|slides|powerpoint|diaporama)",
            r"(présentation|slides).*(sur|à propos|pour)",
        ],
        "output_formats": [OutputFormat.PPTX, OutputFormat.PDF],
    },
    DeliverableType.ARCHIVE: {
        "keywords": [
            "zip", "archive", "package", "bundle", "compresse", "rends-moi",
            "envoie-moi", "livrable"
        ],
        "patterns": [
            r"(mets|package|archive).*(dans|en)\s*(zip|archive)",
            r"(rends|envoie|donne).*moi.*(zip|archive|tout)",
        ],
        "output_formats": [OutputFormat.ZIP],
    },
    DeliverableType.DATA: {
        "keywords": [
            "données", "data", "csv", "json", "excel", "tableau", "dataset",
            "base de données", "database"
        ],
        "patterns": [
            r"(génère|crée|exporte).*(données|data|csv|json|tableau)",
        ],
        "output_formats": [OutputFormat.CSV, OutputFormat.JSON],
    },
}

DEPENDENCY_PATTERNS = [
    # Code avant rapport (pour documenter les choix)
    {
        "pattern": r"(explique|documente|décris).*(choix|implémentation|code).*(dans|pour).*(rapport|document)",
        "from_type": DeliverableType.CODE,
        "to_type": DeliverableType.REPORT,
        "dep_type": DependencyType.CONTENT_REFERENCE,
    },
    # Archive après tout
    {
        "pattern": r"(zip|archive|package).*(tout|le tout|ensemble)",
        "to_type": DeliverableType.ARCHIVE,
        "dep_type": DependencyType.OUTPUT_INPUT,
    },
    # Rapport avec code inclus
    {
        "pattern": r"(rapport|document).*(avec|incluant|contenant).*(code|implémentation)",
        "from_type": DeliverableType.CODE,
        "to_type": DeliverableType.REPORT,
        "dep_type": DependencyType.CONTENT_REFERENCE,
    },
    # Présentation basée sur rapport
    {
        "pattern": r"(présentation|slides).*(basé|à partir|résumant).*(rapport|document|étude)",
        "from_type": DeliverableType.REPORT,
        "to_type": DeliverableType.PRESENTATION,
        "dep_type": DependencyType.CONTENT_REFERENCE,
    },
]


class ProjectAnalyzer:
    
    def __init__(self):
        self.playbook_store = get_playbook_store()
    
    def analyze(self, task: str) -> AnalysisResult:
        task_lower = task.lower()
        
        deliverables = self._detect_deliverables(task, task_lower)
        
        if not deliverables:
            deliverables = self._infer_from_context(task, task_lower)
        
        dependencies = self._detect_dependencies(task_lower, deliverables)
        
        execution_order = self._resolve_execution_order(deliverables, dependencies)
        
        complexity_score = self._calculate_complexity(task, deliverables, dependencies)
        
        is_complex = complexity_score > 0.3 or len(deliverables) > 1
        needs_planning = is_complex or any(d.confidence < 0.7 for d in deliverables)
        
        return AnalysisResult(
            original_task=task,
            is_complex=is_complex,
            deliverables=deliverables,
            dependencies=dependencies,
            execution_order=execution_order,
            needs_planning=needs_planning,
            complexity_score=complexity_score,
        )
    
    def _detect_deliverables(self, task: str, task_lower: str) -> List[DetectedDeliverable]:
        detected = []
        
        for dtype, config in DELIVERABLE_PATTERNS.items():
            keywords_matched = [kw for kw in config["keywords"] if kw in task_lower]
            
            pattern_matched = any(
                re.search(pattern, task_lower)
                for pattern in config["patterns"]
            )
            
            if keywords_matched or pattern_matched:
                confidence = min(1.0, len(keywords_matched) * 0.2 + (0.4 if pattern_matched else 0))
                
                if confidence > 0.2:
                    playbook = self.playbook_store.find_best_match(task)
                    
                    name = self._extract_deliverable_name(task, dtype)
                    
                    detected.append(DetectedDeliverable(
                        deliverable_type=dtype,
                        name=name,
                        description=f"Detected from keywords: {', '.join(keywords_matched[:3])}",
                        keywords_matched=keywords_matched,
                        confidence=confidence,
                        playbook=playbook,
                        output_format=config["output_formats"][0] if config["output_formats"] else None,
                    ))
        
        detected.sort(key=lambda d: d.confidence, reverse=True)
        
        return self._deduplicate_deliverables(detected)
    
    def _infer_from_context(self, task: str, task_lower: str) -> List[DetectedDeliverable]:
        playbook = self.playbook_store.find_best_match(task)
        
        if playbook:
            return [DetectedDeliverable(
                deliverable_type=playbook.deliverable_type,
                name=self._extract_deliverable_name(task, playbook.deliverable_type),
                description="Inferred from playbook match",
                keywords_matched=[],
                confidence=0.5,
                playbook=playbook,
                output_format=playbook.output_formats[0] if playbook.output_formats else None,
            )]
        
        return []
    
    def _extract_deliverable_name(self, task: str, dtype: DeliverableType) -> str:
        patterns = {
            DeliverableType.REPORT: r"(?:rapport|document|article|étude)\s+(?:sur|à propos de|concernant)?\s*(.+?)(?:\.|,|$)",
            DeliverableType.CODE: r"(?:implémente|code|développe)\s+(?:un|une|le|la)?\s*(.+?)(?:\s+en|\s+avec|$)",
            DeliverableType.APP: r"(?:application|app|site)\s+(?:de|pour)?\s*(.+?)(?:\.|,|$)",
            DeliverableType.PRESENTATION: r"(?:présentation|slides)\s+(?:sur|à propos de)?\s*(.+?)(?:\.|,|$)",
        }
        
        if dtype in patterns:
            match = re.search(patterns[dtype], task.lower())
            if match:
                name = match.group(1).strip()[:50]
                if name:
                    return name.title()
        
        type_names = {
            DeliverableType.REPORT: "Rapport",
            DeliverableType.CODE: "Code",
            DeliverableType.APP: "Application",
            DeliverableType.PRESENTATION: "Présentation",
            DeliverableType.ARCHIVE: "Archive",
            DeliverableType.DATA: "Données",
            DeliverableType.WEBSITE: "Site Web",
        }
        return type_names.get(dtype, "Livrable")
    
    def _deduplicate_deliverables(self, deliverables: List[DetectedDeliverable]) -> List[DetectedDeliverable]:
        seen_types = set()
        unique = []
        
        for d in deliverables:
            if d.deliverable_type not in seen_types:
                seen_types.add(d.deliverable_type)
                unique.append(d)
        
        return unique
    
    def _detect_dependencies(
        self, 
        task_lower: str, 
        deliverables: List[DetectedDeliverable]
    ) -> List[DetectedDependency]:
        dependencies = []
        deliverable_types = {d.deliverable_type for d in deliverables}
        
        for dep_config in DEPENDENCY_PATTERNS:
            if re.search(dep_config["pattern"], task_lower):
                from_type = dep_config.get("from_type")
                to_type = dep_config.get("to_type")
                
                if to_type == DeliverableType.ARCHIVE and DeliverableType.ARCHIVE in deliverable_types:
                    for d in deliverables:
                        if d.deliverable_type != DeliverableType.ARCHIVE:
                            dependencies.append(DetectedDependency(
                                from_deliverable=d.name,
                                to_deliverable="Archive",
                                dependency_type=DependencyType.OUTPUT_INPUT,
                                reason="Archive dépend de tous les autres livrables",
                            ))
                
                elif from_type and to_type:
                    if from_type in deliverable_types and to_type in deliverable_types:
                        from_name = next(
                            (d.name for d in deliverables if d.deliverable_type == from_type),
                            str(from_type.value)
                        )
                        to_name = next(
                            (d.name for d in deliverables if d.deliverable_type == to_type),
                            str(to_type.value)
                        )
                        dependencies.append(DetectedDependency(
                            from_deliverable=from_name,
                            to_deliverable=to_name,
                            dependency_type=dep_config["dep_type"],
                            reason=f"Pattern detected: {dep_config['pattern'][:30]}...",
                        ))
        
        return dependencies
    
    def _resolve_execution_order(
        self,
        deliverables: List[DetectedDeliverable],
        dependencies: List[DetectedDependency]
    ) -> List[str]:
        if not deliverables:
            return []
        
        graph: Dict[str, List[str]] = {d.name: [] for d in deliverables}
        in_degree: Dict[str, int] = {d.name: 0 for d in deliverables}
        
        for dep in dependencies:
            if dep.from_deliverable in graph and dep.to_deliverable in graph:
                graph[dep.from_deliverable].append(dep.to_deliverable)
                in_degree[dep.to_deliverable] += 1
        
        queue = [name for name, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            queue.sort()
            current = queue.pop(0)
            order.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(order) != len(deliverables):
            return [d.name for d in deliverables]
        
        return order
    
    def _calculate_complexity(
        self,
        task: str,
        deliverables: List[DetectedDeliverable],
        dependencies: List[DetectedDependency]
    ) -> float:
        score = 0.0
        
        score += min(0.3, len(deliverables) * 0.15)
        
        score += min(0.2, len(dependencies) * 0.1)
        
        word_count = len(task.split())
        if word_count > 50:
            score += 0.2
        elif word_count > 25:
            score += 0.1
        
        complex_keywords = [
            "analyse", "compare", "recherche", "détaillé", "complet",
            "multiple", "plusieurs", "tous", "toutes", "ensemble"
        ]
        task_lower = task.lower()
        score += min(0.2, sum(0.05 for kw in complex_keywords if kw in task_lower))
        
        return min(1.0, score)


def analyze_task(task: str) -> AnalysisResult:
    analyzer = ProjectAnalyzer()
    return analyzer.analyze(task)
