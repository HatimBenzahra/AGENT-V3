"""Error memory for learning from past mistakes."""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib


@dataclass
class ErrorRecord:
    """Record of an error and its resolution."""
    error_hash: str
    error_pattern: str  # Normalized error pattern
    error_sample: str  # Original error message
    solution: str  # What fixed it
    success: bool  # Did the solution work?
    occurrences: int = 1
    last_seen: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_hash": self.error_hash,
            "error_pattern": self.error_pattern,
            "error_sample": self.error_sample,
            "solution": self.solution,
            "success": self.success,
            "occurrences": self.occurrences,
            "last_seen": self.last_seen,
            "context": self.context,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorRecord":
        """Create from dictionary."""
        return cls(
            error_hash=data.get("error_hash", ""),
            error_pattern=data.get("error_pattern", ""),
            error_sample=data.get("error_sample", ""),
            solution=data.get("solution", ""),
            success=data.get("success", False),
            occurrences=data.get("occurrences", 1),
            last_seen=data.get("last_seen", ""),
            context=data.get("context", {}),
        )


class ErrorMemory:
    """Simple persistent memory for errors and their solutions.
    
    This allows the agent to learn from past mistakes and apply
    known solutions more quickly.
    """
    
    def __init__(self, memory_dir: Optional[Path] = None):
        """Initialize error memory.
        
        Args:
            memory_dir: Directory to store memory files.
                       If None, uses in-memory only.
        """
        self.memory_dir = memory_dir
        self.memory_file = memory_dir / "error_memory.json" if memory_dir else None
        self.records: Dict[str, ErrorRecord] = {}
        
        # Load existing memory
        if self.memory_file and self.memory_file.exists():
            self._load()
            
    def _load(self):
        """Load memory from file."""
        if not self.memory_file:
            return
        try:
            with open(self.memory_file, "r") as f:
                data = json.load(f)
                for record_data in data.get("records", []):
                    record = ErrorRecord.from_dict(record_data)
                    self.records[record.error_hash] = record
        except Exception as e:
            print(f"[Memory] Failed to load: {e}")
            
    def _save(self):
        """Save memory to file."""
        if not self.memory_file:
            return
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w") as f:
                json.dump({
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "records": [r.to_dict() for r in self.records.values()],
                }, f, indent=2)
        except Exception as e:
            print(f"[Memory] Failed to save: {e}")
            
    def _normalize_error(self, error: str) -> str:
        """Normalize error message to create a pattern.
        
        This removes specific values like paths, numbers, etc.
        to create a reusable pattern.
        """
        normalized = error
        
        # Remove paths
        normalized = re.sub(r'/[\w/.-]+', '<PATH>', normalized)
        normalized = re.sub(r'\\[\w\\.-]+', '<PATH>', normalized)
        
        # Remove numbers
        normalized = re.sub(r'\b\d+\b', '<NUM>', normalized)
        
        # Remove hex addresses
        normalized = re.sub(r'0x[a-fA-F0-9]+', '<ADDR>', normalized)
        
        # Remove UUIDs
        normalized = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '<UUID>', normalized)
        
        # Remove quoted strings (keep structure)
        normalized = re.sub(r'"[^"]*"', '"<STR>"', normalized)
        normalized = re.sub(r"'[^']*'", "'<STR>'", normalized)
        
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
        
    def _hash_error(self, pattern: str) -> str:
        """Create hash for error pattern."""
        return hashlib.md5(pattern.encode()).hexdigest()[:12]
        
    def record_error(
        self,
        error: str,
        solution: str,
        success: bool,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Record an error and its solution.
        
        Args:
            error: The error message.
            solution: The solution that was tried.
            success: Whether the solution worked.
            context: Additional context (action, params, etc.)
        """
        pattern = self._normalize_error(error)
        error_hash = self._hash_error(pattern)
        
        if error_hash in self.records:
            # Update existing record
            record = self.records[error_hash]
            record.occurrences += 1
            record.last_seen = datetime.now().isoformat()
            
            # Update solution if this one worked better
            if success and not record.success:
                record.solution = solution
                record.success = True
        else:
            # Create new record
            self.records[error_hash] = ErrorRecord(
                error_hash=error_hash,
                error_pattern=pattern,
                error_sample=error[:500],  # Truncate
                solution=solution,
                success=success,
                last_seen=datetime.now().isoformat(),
                context=context or {},
            )
            
        self._save()
        
    def get_solution(self, error: str) -> Optional[str]:
        """Get a known solution for an error.
        
        Args:
            error: The error message.
            
        Returns:
            Solution if known and successful, None otherwise.
        """
        pattern = self._normalize_error(error)
        error_hash = self._hash_error(pattern)
        
        record = self.records.get(error_hash)
        if record and record.success:
            return record.solution
            
        # Try fuzzy matching
        for record in self.records.values():
            if record.success:
                # Check if patterns are similar
                similarity = self._pattern_similarity(pattern, record.error_pattern)
                if similarity > 0.8:
                    return record.solution
                    
        return None
        
    def _pattern_similarity(self, p1: str, p2: str) -> float:
        """Calculate similarity between two patterns."""
        words1 = set(p1.lower().split())
        words2 = set(p2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
        
    def get_frequent_errors(self, limit: int = 10) -> List[ErrorRecord]:
        """Get the most frequently occurring errors.
        
        Args:
            limit: Maximum number of records to return.
            
        Returns:
            List of error records sorted by frequency.
        """
        sorted_records = sorted(
            self.records.values(),
            key=lambda r: r.occurrences,
            reverse=True
        )
        return sorted_records[:limit]
        
    def get_unresolved_errors(self) -> List[ErrorRecord]:
        """Get errors that don't have successful solutions."""
        return [r for r in self.records.values() if not r.success]
        
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        total = len(self.records)
        resolved = sum(1 for r in self.records.values() if r.success)
        total_occurrences = sum(r.occurrences for r in self.records.values())
        
        return {
            "total_error_types": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "total_occurrences": total_occurrences,
            "resolution_rate": resolved / total if total > 0 else 0,
        }
        
    def clear(self):
        """Clear all memory."""
        self.records.clear()
        self._save()
        

class TaskMemory:
    """Memory for task patterns and successful strategies."""
    
    def __init__(self, memory_dir: Optional[Path] = None):
        """Initialize task memory.
        
        Args:
            memory_dir: Directory to store memory files.
        """
        self.memory_dir = memory_dir
        self.memory_file = memory_dir / "task_memory.json" if memory_dir else None
        self.patterns: Dict[str, Dict[str, Any]] = {}
        
        if self.memory_file and self.memory_file.exists():
            self._load()
            
    def _load(self):
        """Load from file."""
        if not self.memory_file:
            return
        try:
            with open(self.memory_file, "r") as f:
                self.patterns = json.load(f).get("patterns", {})
        except Exception:
            pass
            
    def _save(self):
        """Save to file."""
        if not self.memory_file:
            return
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w") as f:
                json.dump({
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "patterns": self.patterns,
                }, f, indent=2)
        except Exception:
            pass
            
    def record_task(
        self,
        task: str,
        strategy: str,
        steps_used: List[str],
        success: bool,
        iterations: int,
    ):
        """Record a successful task completion strategy.
        
        Args:
            task: The task description.
            strategy: The strategy/approach used.
            steps_used: List of steps/actions taken.
            success: Whether the task succeeded.
            iterations: Number of iterations used.
        """
        # Extract task type/pattern
        task_type = self._classify_task(task)
        
        if task_type not in self.patterns:
            self.patterns[task_type] = {
                "strategies": [],
                "avg_iterations": 0,
                "success_rate": 0,
                "total_attempts": 0,
            }
            
        pattern = self.patterns[task_type]
        pattern["total_attempts"] += 1
        
        if success:
            pattern["strategies"].append({
                "strategy": strategy,
                "steps": steps_used[:10],  # Limit
                "iterations": iterations,
            })
            # Keep only last 5 successful strategies
            pattern["strategies"] = pattern["strategies"][-5:]
            
        # Update averages
        pattern["avg_iterations"] = (
            pattern["avg_iterations"] * (pattern["total_attempts"] - 1) + iterations
        ) / pattern["total_attempts"]
        
        success_count = sum(
            1 for s in pattern["strategies"]
        )
        pattern["success_rate"] = success_count / pattern["total_attempts"]
        
        self._save()
        
    def get_strategy(self, task: str) -> Optional[Dict[str, Any]]:
        """Get a recommended strategy for a task.
        
        Args:
            task: The task description.
            
        Returns:
            Strategy info if available.
        """
        task_type = self._classify_task(task)
        
        if task_type in self.patterns:
            pattern = self.patterns[task_type]
            if pattern["strategies"]:
                # Return most recent successful strategy
                return pattern["strategies"][-1]
                
        return None
        
    def _classify_task(self, task: str) -> str:
        """Classify task into a type."""
        task_lower = task.lower()
        
        # Document types
        if any(kw in task_lower for kw in ["pdf", "document", "report"]):
            return "document_generation"
        if any(kw in task_lower for kw in ["article", "essay", "write about"]):
            return "content_writing"
            
        # Code types
        if any(kw in task_lower for kw in ["code", "script", "function", "program"]):
            return "code_generation"
        if any(kw in task_lower for kw in ["debug", "fix", "error"]):
            return "debugging"
            
        # Data types
        if any(kw in task_lower for kw in ["chart", "graph", "visualization"]):
            return "data_visualization"
        if any(kw in task_lower for kw in ["analyze", "analysis"]):
            return "data_analysis"
            
        # Search types
        if any(kw in task_lower for kw in ["search", "find", "look up"]):
            return "information_search"
            
        return "general"
