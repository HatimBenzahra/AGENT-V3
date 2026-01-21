import sqlite3
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager

from .schema import Recipe, RecipeCategory


class KnowledgeStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).parent / "knowledge.db")
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    tags TEXT,
                    examples TEXT,
                    related TEXT,
                    tools_used TEXT,
                    difficulty TEXT DEFAULT 'medium'
                )
            """)
            
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS recipes_fts USING fts5(
                    id,
                    title,
                    question,
                    answer,
                    tags,
                    content='recipes',
                    content_rowid='rowid'
                )
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS recipes_ai AFTER INSERT ON recipes BEGIN
                    INSERT INTO recipes_fts(rowid, id, title, question, answer, tags)
                    VALUES (new.rowid, new.id, new.title, new.question, new.answer, new.tags);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS recipes_ad AFTER DELETE ON recipes BEGIN
                    INSERT INTO recipes_fts(recipes_fts, rowid, id, title, question, answer, tags)
                    VALUES ('delete', old.rowid, old.id, old.title, old.question, old.answer, old.tags);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS recipes_au AFTER UPDATE ON recipes BEGIN
                    INSERT INTO recipes_fts(recipes_fts, rowid, id, title, question, answer, tags)
                    VALUES ('delete', old.rowid, old.id, old.title, old.question, old.answer, old.tags);
                    INSERT INTO recipes_fts(rowid, id, title, question, answer, tags)
                    VALUES (new.rowid, new.id, new.title, new.question, new.answer, new.tags);
                END
            """)
            
            conn.commit()
    
    def add_recipe(self, recipe: Recipe) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO recipes 
                (id, title, category, question, answer, tags, examples, related, tools_used, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recipe.id,
                recipe.title,
                recipe.category.value,
                recipe.question,
                recipe.answer,
                "|".join(recipe.tags),
                "|".join(recipe.examples),
                "|".join(recipe.related),
                "|".join(recipe.tools_used),
                recipe.difficulty,
            ))
            conn.commit()
    
    def add_recipes(self, recipes: List[Recipe]) -> None:
        for recipe in recipes:
            self.add_recipe(recipe)
    
    def search(self, query: str, limit: int = 10, category: Optional[RecipeCategory] = None) -> List[Recipe]:
        with self._get_connection() as conn:
            if category:
                cursor = conn.execute("""
                    SELECT r.* FROM recipes r
                    JOIN recipes_fts fts ON r.id = fts.id
                    WHERE recipes_fts MATCH ? AND r.category = ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, category.value, limit))
            else:
                cursor = conn.execute("""
                    SELECT r.* FROM recipes r
                    JOIN recipes_fts fts ON r.id = fts.id
                    WHERE recipes_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, limit))
            
            return [self._row_to_recipe(row) for row in cursor.fetchall()]
    
    def get_by_category(self, category: RecipeCategory, limit: int = 50) -> List[Recipe]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM recipes WHERE category = ? LIMIT ?",
                (category.value, limit)
            )
            return [self._row_to_recipe(row) for row in cursor.fetchall()]
    
    def get_by_id(self, recipe_id: str) -> Optional[Recipe]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM recipes WHERE id = ?",
                (recipe_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_recipe(row)
            return None
    
    def get_all(self) -> List[Recipe]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM recipes")
            return [self._row_to_recipe(row) for row in cursor.fetchall()]
    
    def count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM recipes")
            return cursor.fetchone()[0]
    
    def _row_to_recipe(self, row: sqlite3.Row) -> Recipe:
        return Recipe(
            id=row["id"],
            title=row["title"],
            category=RecipeCategory(row["category"]),
            question=row["question"],
            answer=row["answer"],
            tags=row["tags"].split("|") if row["tags"] else [],
            examples=row["examples"].split("|") if row["examples"] else [],
            related=row["related"].split("|") if row["related"] else [],
            tools_used=row["tools_used"].split("|") if row["tools_used"] else [],
            difficulty=row["difficulty"],
        )
    
    def clear(self) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM recipes")
            conn.execute("DELETE FROM recipes_fts")
            conn.commit()
