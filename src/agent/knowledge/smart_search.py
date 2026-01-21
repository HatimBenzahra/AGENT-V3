from dataclasses import dataclass
from typing import List, Optional
import asyncio

from .schema import Recipe, RecipeCategory
from .store import KnowledgeStore


@dataclass
class SearchResult:
    source: str
    title: str
    content: str
    relevance: float
    url: Optional[str] = None
    recipe: Optional[Recipe] = None


class SmartSearch:
    TRUSTED_SOURCES = [
        "docs.python.org",
        "developer.mozilla.org",
        "stackoverflow.com",
        "github.com",
        "cppreference.com",
        "en.cppreference.com",
        "latex-project.org",
        "overleaf.com",
    ]
    
    def __init__(self, knowledge_store: Optional[KnowledgeStore] = None):
        self.kb = knowledge_store
        
    async def search(
        self,
        query: str,
        category: Optional[RecipeCategory] = None,
        include_web: bool = False,
        max_results: int = 5,
    ) -> List[SearchResult]:
        results: List[SearchResult] = []
        
        if self.kb:
            kb_results = self._search_local_kb(query, category, max_results)
            results.extend(kb_results)
        
        if include_web and len(results) < max_results:
            web_results = await self._search_web(query, max_results - len(results))
            results.extend(web_results)
        
        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:max_results]
    
    def _search_local_kb(
        self,
        query: str,
        category: Optional[RecipeCategory] = None,
        max_results: int = 5,
    ) -> List[SearchResult]:
        if self.kb is None:
            return []
        recipes = self.kb.search(query, limit=max_results, category=category)
        
        results = []
        for i, recipe in enumerate(recipes):
            relevance = 1.0 - (i * 0.1)
            results.append(SearchResult(
                source="knowledge_base",
                title=recipe.title,
                content=recipe.answer,
                relevance=relevance,
                recipe=recipe,
            ))
        
        return results
    
    async def _search_web(
        self,
        query: str,
        max_results: int = 3,
    ) -> List[SearchResult]:
        return []
    
    def format_results_for_agent(self, results: List[SearchResult]) -> str:
        if not results:
            return "Aucune information pertinente trouvée."
        
        lines = ["## Informations trouvées:\n"]
        
        for i, result in enumerate(results, 1):
            lines.append(f"### {i}. {result.title}")
            lines.append(f"*Source: {result.source}*\n")
            lines.append(result.content)
            lines.append("")
        
        return "\n".join(lines)


async def search_knowledge(
    query: str,
    kb_path: Optional[str] = None,
    category: Optional[RecipeCategory] = None,
    include_web: bool = False,
) -> str:
    from .loader import init_knowledge_base
    
    store = init_knowledge_base(kb_path)
    searcher = SmartSearch(store)
    results = await searcher.search(query, category=category, include_web=include_web)
    return searcher.format_results_for_agent(results)
