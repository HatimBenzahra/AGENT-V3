"""Output validation for agent actions."""
import ast
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext


class ValidationStatus(Enum):
    """Status of validation."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of output validation."""
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None


class OutputValidator:
    """Validates outputs from agent actions."""
    
    def __init__(self, docker_context: Optional["DockerExecutionContext"] = None):
        """Initialize validator.
        
        Args:
            docker_context: Docker execution context for file operations.
        """
        self.docker_context = docker_context
        
    async def validate(
        self,
        action: str,
        result: str,
        params: Dict[str, Any],
    ) -> ValidationResult:
        """Validate the result of an action.
        
        Args:
            action: The action that was executed (e.g., "write_file").
            result: The result/observation from the action.
            params: The parameters that were passed to the action.
            
        Returns:
            ValidationResult with status and details.
        """
        validators = {
            "write_file": self._validate_write_file,
            "execute_command": self._validate_command,
            "read_file": self._validate_read_file,
            "create_pdf": self._validate_pdf,
            "web_search": self._validate_search,
        }
        
        validator = validators.get(action)
        if not validator:
            return ValidationResult(
                status=ValidationStatus.SKIPPED,
                message=f"No validator for action: {action}",
            )
            
        return await validator(result, params)
        
    async def _validate_write_file(
        self, result: str, params: Dict[str, Any]
    ) -> ValidationResult:
        """Validate file write operation."""
        file_path = params.get("file_path", "")
        content = params.get("content", "")
        
        # Check if success message
        if "successfully" not in result.lower() and "error" not in result.lower():
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="Unclear if file was written successfully",
            )
            
        if "error" in result.lower():
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="File write failed",
                details={"error": result},
            )
            
        # Validate based on file type
        ext = Path(file_path).suffix.lower()
        
        if ext == ".py":
            return self._validate_python_syntax(content, file_path)
        elif ext == ".json":
            return self._validate_json_syntax(content, file_path)
        elif ext in [".md", ".txt"]:
            return self._validate_text_file(content, file_path)
            
        return ValidationResult(
            status=ValidationStatus.VALID,
            message="File written successfully",
            details={"path": file_path, "size": len(content)},
        )
        
    def _validate_python_syntax(self, content: str, file_path: str) -> ValidationResult:
        """Validate Python code syntax."""
        try:
            ast.parse(content)
            return ValidationResult(
                status=ValidationStatus.VALID,
                message="Python syntax is valid",
                details={"path": file_path},
            )
        except SyntaxError as e:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"Python syntax error: {e.msg}",
                details={
                    "line": e.lineno,
                    "offset": e.offset,
                    "text": e.text,
                },
                suggestions=[
                    f"Check line {e.lineno} for syntax issues",
                    "Ensure proper indentation",
                    "Check for missing colons, brackets, or quotes",
                ],
            )
            
    def _validate_json_syntax(self, content: str, file_path: str) -> ValidationResult:
        """Validate JSON syntax."""
        import json
        try:
            json.loads(content)
            return ValidationResult(
                status=ValidationStatus.VALID,
                message="JSON syntax is valid",
                details={"path": file_path},
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"JSON syntax error: {e.msg}",
                details={
                    "line": e.lineno,
                    "column": e.colno,
                },
                suggestions=[
                    "Check for trailing commas",
                    "Ensure all strings are double-quoted",
                    "Verify bracket matching",
                ],
            )
            
    def _validate_text_file(self, content: str, file_path: str) -> ValidationResult:
        """Validate text file content."""
        if not content.strip():
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="File is empty or contains only whitespace",
                details={"path": file_path},
                suggestions=["Consider adding content to the file"],
            )
            
        return ValidationResult(
            status=ValidationStatus.VALID,
            message="Text file is valid",
            details={"path": file_path, "lines": content.count('\n') + 1},
        )
        
    async def _validate_command(
        self, result: str, params: Dict[str, Any]
    ) -> ValidationResult:
        """Validate command execution."""
        command = params.get("command", "")
        
        # Check for common error patterns
        error_patterns = [
            (r"command not found", "Command not found - may need to install"),
            (r"No such file or directory", "File or directory does not exist"),
            (r"Permission denied", "Permission denied - may need different permissions"),
            (r"ModuleNotFoundError", "Python module not installed"),
            (r"Error:|ERROR:|error:", "Generic error occurred"),
            (r"Traceback", "Python exception occurred"),
            (r"exit code: [1-9]", "Command exited with non-zero status"),
        ]
        
        for pattern, message in error_patterns:
            if re.search(pattern, result, re.IGNORECASE):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=message,
                    details={"command": command, "output": result[:500]},
                )
                
        # Check for success indicators
        success_patterns = [
            r"exit code: 0",
            r"successfully",
            r"done",
            r"completed",
        ]
        
        for pattern in success_patterns:
            if re.search(pattern, result, re.IGNORECASE):
                return ValidationResult(
                    status=ValidationStatus.VALID,
                    message="Command executed successfully",
                    details={"command": command},
                )
                
        # Uncertain outcome
        return ValidationResult(
            status=ValidationStatus.WARNING,
            message="Command outcome unclear",
            details={"command": command, "output": result[:200]},
        )
        
    async def _validate_read_file(
        self, result: str, params: Dict[str, Any]
    ) -> ValidationResult:
        """Validate file read operation."""
        file_path = params.get("file_path", "")
        
        if "error" in result.lower() or "not found" in result.lower():
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="Failed to read file",
                details={"path": file_path, "error": result},
            )
            
        if not result.strip():
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="File is empty",
                details={"path": file_path},
            )
            
        return ValidationResult(
            status=ValidationStatus.VALID,
            message="File read successfully",
            details={"path": file_path, "size": len(result)},
        )
        
    async def _validate_pdf(
        self, result: str, params: Dict[str, Any]
    ) -> ValidationResult:
        """Validate PDF creation."""
        file_path = params.get("file_path", "")
        
        if "error" in result.lower():
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="PDF creation failed",
                details={"path": file_path, "error": result},
            )
            
        if "successfully" in result.lower() or "created" in result.lower():
            return ValidationResult(
                status=ValidationStatus.VALID,
                message="PDF created successfully",
                details={"path": file_path},
            )
            
        return ValidationResult(
            status=ValidationStatus.WARNING,
            message="PDF creation status unclear",
            details={"path": file_path, "result": result[:200]},
        )
        
    async def _validate_search(
        self, result: str, params: Dict[str, Any]
    ) -> ValidationResult:
        """Validate search results."""
        query = params.get("query", "")
        
        if "no results" in result.lower():
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="No search results found",
                details={"query": query},
                suggestions=[
                    "Try different keywords",
                    "Use broader search terms",
                    "Check spelling",
                ],
            )
            
        # Count results
        result_count = len(re.findall(r'^\d+\.', result, re.MULTILINE))
        
        if result_count == 0:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="Search may have failed",
                details={"query": query},
            )
            
        return ValidationResult(
            status=ValidationStatus.VALID,
            message=f"Found {result_count} results",
            details={"query": query, "count": result_count},
        )


class TaskValidator:
    """Validates overall task completion."""
    
    def __init__(self):
        """Initialize task validator."""
        self.action_history: List[Dict[str, Any]] = []
        
    def record_action(
        self,
        action: str,
        params: Dict[str, Any],
        result: str,
        validation: ValidationResult,
    ):
        """Record an action and its validation result."""
        self.action_history.append({
            "action": action,
            "params": params,
            "result_preview": result[:200],
            "validation": {
                "status": validation.status.value,
                "message": validation.message,
            },
        })
        
    def assess_task_completion(self, task: str, final_answer: str) -> ValidationResult:
        """Assess if the task was completed successfully.
        
        Args:
            task: The original task description.
            final_answer: The agent's final answer.
            
        Returns:
            ValidationResult for task completion.
        """
        # Count successful vs failed actions
        successful = sum(
            1 for a in self.action_history 
            if a["validation"]["status"] == "valid"
        )
        failed = sum(
            1 for a in self.action_history 
            if a["validation"]["status"] == "invalid"
        )
        warnings = sum(
            1 for a in self.action_history 
            if a["validation"]["status"] == "warning"
        )
        
        total = len(self.action_history)
        
        # Check for common task completion indicators
        task_lower = task.lower()
        answer_lower = final_answer.lower()
        
        completion_indicators = []
        
        # File creation tasks
        if any(kw in task_lower for kw in ["create", "write", "generate", "make"]):
            file_actions = [
                a for a in self.action_history 
                if a["action"] in ["write_file", "create_pdf"]
            ]
            if file_actions:
                completion_indicators.append("file_created")
                
        # Check if final answer references outputs
        if "download" in answer_lower or "file" in answer_lower or "created" in answer_lower:
            completion_indicators.append("output_mentioned")
            
        # Determine overall status
        if failed > successful:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message="Task likely incomplete due to multiple failures",
                details={
                    "total_actions": total,
                    "successful": successful,
                    "failed": failed,
                    "warnings": warnings,
                },
                suggestions=[
                    "Review failed actions",
                    "Try alternative approaches",
                ],
            )
            
        if failed > 0:
            return ValidationResult(
                status=ValidationStatus.WARNING,
                message="Task completed with some failures",
                details={
                    "total_actions": total,
                    "successful": successful,
                    "failed": failed,
                    "completion_indicators": completion_indicators,
                },
            )
            
        return ValidationResult(
            status=ValidationStatus.VALID,
            message="Task appears to be completed successfully",
            details={
                "total_actions": total,
                "successful": successful,
                "completion_indicators": completion_indicators,
            },
        )
        
    def reset(self):
        """Reset action history for new task."""
        self.action_history.clear()
