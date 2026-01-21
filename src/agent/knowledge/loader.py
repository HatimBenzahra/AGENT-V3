import yaml
from pathlib import Path
from typing import List, Optional

from .schema import Recipe, RecipeCategory
from .store import KnowledgeStore


def load_knowledge_from_yaml(yaml_path: str, store: KnowledgeStore) -> int:
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not data or "recipes" not in data:
        return 0
    
    category_str = data.get("category", "system")
    try:
        category = RecipeCategory(category_str)
    except ValueError:
        category = RecipeCategory.SYSTEM
    
    recipes = []
    for item in data["recipes"]:
        recipe = Recipe(
            title=item["title"],
            category=category,
            question=item["question"],
            answer=item["answer"],
            tags=item.get("tags", []),
            examples=item.get("examples", []),
            related=item.get("related", []),
            tools_used=item.get("tools_used", []),
            difficulty=item.get("difficulty", "medium"),
        )
        recipes.append(recipe)
    
    store.add_recipes(recipes)
    return len(recipes)


def load_all_knowledge(domains_dir: str, store: KnowledgeStore) -> int:
    domains_path = Path(domains_dir)
    if not domains_path.exists():
        return 0
    
    total = 0
    for yaml_file in domains_path.glob("*.yaml"):
        count = load_knowledge_from_yaml(str(yaml_file), store)
        total += count
    
    for yaml_file in domains_path.glob("*.yml"):
        count = load_knowledge_from_yaml(str(yaml_file), store)
        total += count
    
    return total


_kb_instance: Optional[KnowledgeStore] = None

def init_knowledge_base(db_path: Optional[str] = None, force_reload: bool = False) -> KnowledgeStore:
    global _kb_instance
    
    if _kb_instance is not None and not force_reload:
        return _kb_instance
    
    store = KnowledgeStore(db_path)
    
    if store.count() == 0 or force_reload:
        if force_reload:
            store.clear()
        domains_dir = Path(__file__).parent / "domains"
        load_all_knowledge(str(domains_dir), store)
    
    _kb_instance = store
    return store
