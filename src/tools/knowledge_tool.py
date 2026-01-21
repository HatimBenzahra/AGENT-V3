from typing import Any, Dict, Optional

from src.tools.base import Tool
from src.agent.knowledge import SmartSearch, init_knowledge_base, RecipeCategory


class KnowledgeSearchTool(Tool):
    
    def __init__(self):
        super().__init__()
        self._store = None
        self._searcher = None
    
    @property
    def _kb_store(self):
        if self._store is None:
            self._store = init_knowledge_base()
        return self._store
    
    @property
    def _smart_search(self):
        if self._searcher is None:
            self._searcher = SmartSearch(self._kb_store)
        return self._searcher

    @property
    def name(self) -> str:
        return "search_knowledge"

    @property
    def description(self) -> str:
        return """Search the knowledge base for how-to guides, best practices, and technical recipes.
Use this tool when you need guidance on:
- How to create documents (LaTeX, PDF, Markdown)
- Programming best practices (C, Python, etc.)
- Common commands and configurations (Git, Docker, SSH)
- File operations and system administration

This returns detailed step-by-step instructions and code examples."""

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query describing what you need help with (e.g., 'create PDF with LaTeX', 'Makefile for C project', 'Docker compose setup')"
                },
                "category": {
                    "type": "string",
                    "enum": ["documents", "code_c_cpp", "code_python", "web_frontend", "web_backend", "devops", "system"],
                    "description": "Optional category to filter results"
                }
            },
            "required": ["query"]
        }

    async def execute(self, query: str, category: Optional[str] = None, **kwargs: Any) -> str:
        cat = None
        if category:
            try:
                cat = RecipeCategory(category)
            except ValueError:
                pass
        
        results = await self._smart_search.search(
            query=query,
            category=cat,
            include_web=False,
            max_results=3
        )
        
        if not results:
            return f"No knowledge found for: {query}. Try a different search or proceed with your best judgment."
        
        return self._smart_search.format_results_for_agent(results)
