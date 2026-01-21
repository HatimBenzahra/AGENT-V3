import json
import re
from typing import Optional, Dict, Any

from src.models.llm_client import LLMClient
from src.agent.planning.schema import (
    ProjectPlan, Phase, Task, Deliverable, PlanStatus
)


PLANNING_SYSTEM_PROMPT = """Tu es un expert en gestion de projet technique. Ton rôle est d'analyser un énoncé de projet et de créer un plan d'exécution structuré et intelligent.

## TA MÉTHODE DE TRAVAIL

### ÉTAPE 1 - LECTURE COMPLÈTE
Lis l'énoncé EN ENTIER avant de commencer. Ne saute aucune partie.

### ÉTAPE 2 - EXTRACTION DES INFORMATIONS CLÉS
Identifie et note:
- L'OBJECTIF PRINCIPAL: Qu'est-ce qui doit être produit au final?
- LES LIVRABLES: Quels fichiers/documents doivent être rendus? Dans quel format?
- LA DEADLINE: Quelle est la date limite?
- LES CONTRAINTES: Langage imposé? Format? Restrictions?
- LES RESSOURCES FOURNIES: Code donné? Fichiers de test? Documentation?
- LES CRITÈRES D'ÉVALUATION: Comment le travail sera-t-il jugé?

### ÉTAPE 3 - DÉCOMPOSITION EN PHASES
Découpe le projet en 3-6 phases LOGIQUES:
- Chaque phase a UN objectif clair
- Les phases respectent les dépendances naturelles
- On ne peut pas tester avant d'implémenter
- On ne peut pas documenter avant de comprendre

### ÉTAPE 4 - DÉTAIL DES TÂCHES
Pour chaque phase, liste 2-5 tâches:
- Chaque tâche est ACTIONNABLE (verbe d'action)
- Chaque tâche a un critère de DONE clair
- Les tâches sont ordonnées logiquement

### ÉTAPE 5 - VALIDATION
Vérifie:
- Tout l'énoncé est couvert
- Les livrables finaux sont bien définis
- Le plan est réalisable

## FORMAT DE SORTIE

Tu dois retourner UNIQUEMENT un JSON valide (pas de texte avant ou après):

```json
{
  "title": "Titre court et descriptif du projet",
  "objective": "L'objectif principal en 1-2 phrases",
  "deadline": "Date si mentionnée, sinon null",
  "constraints": ["contrainte 1", "contrainte 2"],
  "resources_provided": ["ressource 1", "ressource 2"],
  "deliverables": [
    {
      "name": "Nom du livrable",
      "format": "format (pdf, zip, folder, etc.)",
      "description": "Description courte"
    }
  ],
  "phases": [
    {
      "name": "Nom de la phase",
      "objective": "Objectif de cette phase",
      "order": 1,
      "tasks": [
        {
          "name": "Nom de la tâche (verbe d'action)",
          "done_when": "Critère de succès mesurable"
        }
      ]
    }
  ]
}
```

## RÈGLES IMPORTANTES

1. Sois SPÉCIFIQUE au projet donné - pas de phases génériques
2. Les tâches doivent être CONCRÈTES et ACTIONNABLES
3. Les critères "done_when" doivent être VÉRIFIABLES
4. Respecte l'ORDRE LOGIQUE des dépendances
5. Ne mets PAS plus de 6 phases ni plus de 5 tâches par phase
6. Génère UNIQUEMENT le JSON, rien d'autre"""


class PlanningEngine:
    
    def __init__(self):
        self.llm = LLMClient()
    
    async def create_plan(self, request: str) -> ProjectPlan:
        messages = [
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {"role": "user", "content": f"Crée un plan d'exécution pour ce projet:\n\n{request}"}
        ]
        
        response = await self.llm.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        plan_data = self._parse_response(response)
        
        if plan_data:
            return self._build_plan(request, plan_data)
        else:
            return self._create_fallback_plan(request)
    
    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                return json.loads(json_match.group(1))
            
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            
        except json.JSONDecodeError as e:
            print(f"[PlanningEngine] JSON parse error: {e}")
        
        return None
    
    def _build_plan(self, request: str, data: Dict[str, Any]) -> ProjectPlan:
        deliverables = []
        for d in data.get("deliverables", []):
            name = d.get("name", "")
            if not name or len(name) > 100:
                continue
            deliverables.append(Deliverable(
                name=name,
                format=d.get("format") or "fichier",
                description=d.get("description", ""),
            ))
        
        phases = []
        for i, p in enumerate(data.get("phases", [])):
            tasks = []
            for t in p.get("tasks", []):
                tasks.append(Task(
                    name=t.get("name", "Tâche"),
                    done_when=t.get("done_when", ""),
                ))
            
            phases.append(Phase(
                name=p.get("name", f"Phase {i+1}"),
                objective=p.get("objective", ""),
                order=p.get("order", i+1),
                depends_on=p.get("depends_on", []),
                tasks=tasks,
            ))
        
        return ProjectPlan(
            title=data.get("title", "Projet"),
            objective=data.get("objective", ""),
            original_request=request,
            deadline=data.get("deadline"),
            constraints=data.get("constraints", []),
            resources_provided=data.get("resources_provided", []),
            deliverables=deliverables,
            phases=phases,
            status=PlanStatus.PENDING_APPROVAL,
        )
    
    def _create_fallback_plan(self, request: str) -> ProjectPlan:
        return ProjectPlan(
            title="Projet",
            objective="Analyser et exécuter la demande",
            original_request=request,
            deliverables=[],
            phases=[
                Phase(
                    name="Analyse",
                    objective="Comprendre la demande",
                    order=1,
                    tasks=[
                        Task(name="Analyser l'énoncé", done_when="Objectifs identifiés"),
                        Task(name="Identifier les livrables", done_when="Liste des livrables claire"),
                    ]
                ),
                Phase(
                    name="Implémentation",
                    objective="Réaliser le travail demandé",
                    order=2,
                    tasks=[
                        Task(name="Exécuter la tâche principale", done_when="Travail terminé"),
                    ]
                ),
                Phase(
                    name="Finalisation",
                    objective="Vérifier et livrer",
                    order=3,
                    tasks=[
                        Task(name="Vérifier le résultat", done_when="Tout fonctionne"),
                        Task(name="Préparer les livrables", done_when="Fichiers prêts"),
                    ]
                ),
            ],
            status=PlanStatus.PENDING_APPROVAL,
        )
    
    async def refine_plan(self, plan: ProjectPlan, feedback: str) -> ProjectPlan:
        current_plan_json = json.dumps(plan.to_dict(), indent=2, ensure_ascii=False)
        
        messages = [
            {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
            {"role": "user", "content": f"""Voici le plan actuel:

```json
{current_plan_json}
```

L'utilisateur demande ces modifications:
{feedback}

Génère le plan mis à jour en tenant compte du feedback."""}
        ]
        
        response = await self.llm.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        plan_data = self._parse_response(response)
        
        if plan_data:
            new_plan = self._build_plan(plan.original_request, plan_data)
            new_plan.user_modified = True
            return new_plan
        
        return plan
    
    def update_task_status(self, plan: ProjectPlan, task_id: str, status: str, output: Optional[str] = None) -> ProjectPlan:
        from src.agent.planning.schema import TaskStatus
        
        task = plan.get_task_by_id(task_id)
        if task:
            task.status = TaskStatus(status)
            if output:
                task.output = output
        
        all_completed = all(
            t.status == TaskStatus.COMPLETED
            for p in plan.phases
            for t in p.tasks
        )
        
        if all_completed:
            plan.status = PlanStatus.COMPLETED
        elif any(t.status == TaskStatus.FAILED for p in plan.phases for t in p.tasks):
            plan.status = PlanStatus.FAILED
        elif any(t.status == TaskStatus.IN_PROGRESS for p in plan.phases for t in p.tasks):
            plan.status = PlanStatus.IN_PROGRESS
        
        return plan


async def create_plan(request: str) -> ProjectPlan:
    engine = PlanningEngine()
    return await engine.create_plan(request)
