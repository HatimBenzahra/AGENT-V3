import sqlite3
import os
from pathlib import Path
from typing import List, Optional
import yaml

from src.agent.playbooks.schema import Playbook, DeliverableType


class PlaybookStore:
    
    DEFAULT_PLAYBOOKS_DIR = Path(__file__).parent / "defaults"
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = Path(__file__).parent.parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "playbooks.db")
        
        self.db_path = db_path
        self._init_db()
        self._load_defaults()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playbooks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                deliverable_type TEXT NOT NULL,
                triggers TEXT NOT NULL,
                content TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS playbooks_fts USING fts5(
                id,
                name,
                triggers,
                examples,
                content='playbooks',
                content_rowid='rowid'
            )
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS playbooks_ai AFTER INSERT ON playbooks BEGIN
                INSERT INTO playbooks_fts(rowid, id, name, triggers, examples)
                VALUES (new.rowid, new.id, new.name, new.triggers, 
                    (SELECT group_concat(value) FROM json_each(json_extract(new.content, '$.examples'))));
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS playbooks_ad AFTER DELETE ON playbooks BEGIN
                INSERT INTO playbooks_fts(playbooks_fts, rowid, id, name, triggers, examples)
                VALUES ('delete', old.rowid, old.id, old.name, old.triggers, '');
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS playbooks_au AFTER UPDATE ON playbooks BEGIN
                INSERT INTO playbooks_fts(playbooks_fts, rowid, id, name, triggers, examples)
                VALUES ('delete', old.rowid, old.id, old.name, old.triggers, '');
                INSERT INTO playbooks_fts(rowid, id, name, triggers, examples)
                VALUES (new.rowid, new.id, new.name, new.triggers,
                    (SELECT group_concat(value) FROM json_each(json_extract(new.content, '$.examples'))));
            END
        """)
        
        conn.commit()
        conn.close()
    
    def _load_defaults(self):
        if not self.DEFAULT_PLAYBOOKS_DIR.exists():
            return
        
        for yaml_file in self.DEFAULT_PLAYBOOKS_DIR.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            try:
                playbook = Playbook.from_yaml(content)
                self.upsert(playbook)
            except Exception as e:
                print(f"[PlaybookStore] Failed to load {yaml_file}: {e}")
    
    def upsert(self, playbook: Playbook):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        import json
        triggers_str = ",".join(playbook.triggers)
        content_json = json.dumps(playbook.to_dict(), ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO playbooks (id, name, deliverable_type, triggers, content)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                deliverable_type = excluded.deliverable_type,
                triggers = excluded.triggers,
                content = excluded.content,
                updated_at = CURRENT_TIMESTAMP
        """, (playbook.id, playbook.name, playbook.deliverable_type.value, triggers_str, content_json))
        
        conn.commit()
        conn.close()
    
    def get_by_id(self, playbook_id: str) -> Optional[Playbook]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT content FROM playbooks WHERE id = ?", (playbook_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            import json
            data = json.loads(row[0])
            return Playbook.from_dict(data)
        return None
    
    def get_by_type(self, deliverable_type: DeliverableType) -> List[Playbook]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT content FROM playbooks WHERE deliverable_type = ?",
            (deliverable_type.value,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        import json
        return [Playbook.from_dict(json.loads(row[0])) for row in rows]
    
    def search(self, query: str, limit: int = 5) -> List[Playbook]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        search_query = " OR ".join(query.lower().split())
        
        cursor.execute("""
            SELECT p.content, bm25(playbooks_fts) as score
            FROM playbooks_fts fts
            JOIN playbooks p ON fts.id = p.id
            WHERE playbooks_fts MATCH ?
            ORDER BY score
            LIMIT ?
        """, (search_query, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        import json
        return [Playbook.from_dict(json.loads(row[0])) for row in rows]
    
    def find_best_match(self, text: str) -> Optional[Playbook]:
        text_lower = text.lower()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, triggers, content FROM playbooks")
        rows = cursor.fetchall()
        conn.close()
        
        best_match = None
        best_score = 0
        
        import json
        for row in rows:
            triggers = row[1].split(",")
            score = sum(1 for trigger in triggers if trigger.strip() in text_lower)
            
            if score > best_score:
                best_score = score
                best_match = Playbook.from_dict(json.loads(row[2]))
        
        if best_match:
            return best_match
        
        fts_results = self.search(text, limit=1)
        return fts_results[0] if fts_results else None
    
    def get_all(self) -> List[Playbook]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT content FROM playbooks")
        rows = cursor.fetchall()
        conn.close()
        
        import json
        return [Playbook.from_dict(json.loads(row[0])) for row in rows]
    
    def delete(self, playbook_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM playbooks WHERE id = ?", (playbook_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted


_default_store: Optional[PlaybookStore] = None


def get_playbook_store() -> PlaybookStore:
    global _default_store
    if _default_store is None:
        _default_store = PlaybookStore()
    return _default_store
