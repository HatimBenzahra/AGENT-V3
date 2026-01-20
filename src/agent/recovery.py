"""Self-healing and error recovery strategies for the agent."""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ErrorType(Enum):
    """Types of errors that can be recovered from."""
    PIP_INSTALL = "pip_install"
    MODULE_NOT_FOUND = "module_not_found"
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    COMMAND_NOT_FOUND = "command_not_found"
    SYNTAX_ERROR = "syntax_error"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass
class RecoveryAction:
    """A recovery action to try."""
    description: str
    action_type: str  # "execute_command", "write_file", "modify_params"
    params: Dict[str, Any]
    priority: int = 0


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    error_type: ErrorType
    original_error: str
    recovery_action: Optional[RecoveryAction]
    new_observation: Optional[str] = None
    attempts: int = 0


class ErrorPatterns:
    """Regex patterns to detect error types."""
    
    PATTERNS: Dict[ErrorType, List[str]] = {
        ErrorType.PIP_INSTALL: [
            r"pip install",
            r"Could not find a version",
            r"No matching distribution",
            r"ERROR: Could not install packages",
        ],
        ErrorType.MODULE_NOT_FOUND: [
            r"ModuleNotFoundError: No module named '([^']+)'",
            r"ImportError: No module named '([^']+)'",
            r"No module named (\w+)",
        ],
        ErrorType.FILE_NOT_FOUND: [
            r"FileNotFoundError",
            r"No such file or directory",
            r"File not found",
            r"\[Errno 2\]",
        ],
        ErrorType.PERMISSION_DENIED: [
            r"PermissionError",
            r"Permission denied",
            r"\[Errno 13\]",
        ],
        ErrorType.COMMAND_NOT_FOUND: [
            r"command not found",
            r"not found",
            r"No such command",
            r"bash: (\w+): not found",
        ],
        ErrorType.SYNTAX_ERROR: [
            r"SyntaxError",
            r"IndentationError",
            r"invalid syntax",
        ],
        ErrorType.TIMEOUT: [
            r"TimeoutError",
            r"timed out",
            r"timeout",
        ],
        ErrorType.NETWORK_ERROR: [
            r"ConnectionError",
            r"ConnectionRefusedError",
            r"Network is unreachable",
            r"Name or service not known",
        ],
    }
    
    @classmethod
    def detect_error_type(cls, error_message: str) -> Tuple[ErrorType, Optional[str]]:
        """Detect the type of error and extract relevant info.
        
        Returns:
            Tuple of (ErrorType, extracted_value) where extracted_value
            might be a module name, file path, etc.
        """
        for error_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, error_message, re.IGNORECASE)
                if match:
                    # Try to extract useful info from groups
                    extracted = match.group(1) if match.groups() else None
                    return error_type, extracted
        
        return ErrorType.UNKNOWN, None


class RecoveryStrategies:
    """Collection of recovery strategies for different error types."""
    
    @staticmethod
    def get_strategies(
        error_type: ErrorType,
        extracted_value: Optional[str] = None,
        original_action: Optional[str] = None,
        original_params: Optional[Dict] = None,
    ) -> List[RecoveryAction]:
        """Get recovery strategies for an error type.
        
        Args:
            error_type: The detected error type.
            extracted_value: Value extracted from error (e.g., module name).
            original_action: The action that failed.
            original_params: The parameters of the failed action.
            
        Returns:
            List of RecoveryAction to try, ordered by priority.
        """
        strategies: List[RecoveryAction] = []
        
        if error_type == ErrorType.MODULE_NOT_FOUND:
            module = extracted_value or "unknown"
            # Common module name mappings
            pip_name_map = {
                "cv2": "opencv-python",
                "PIL": "Pillow",
                "sklearn": "scikit-learn",
                "yaml": "PyYAML",
                "bs4": "beautifulsoup4",
            }
            pip_name = pip_name_map.get(module, module)
            
            strategies = [
                RecoveryAction(
                    description=f"Install {pip_name} with pip",
                    action_type="execute_command",
                    params={"command": f"pip install {pip_name}"},
                    priority=1,
                ),
                RecoveryAction(
                    description=f"Install {pip_name} with pip3",
                    action_type="execute_command",
                    params={"command": f"pip3 install {pip_name}"},
                    priority=2,
                ),
                RecoveryAction(
                    description=f"Install {pip_name} with python -m pip",
                    action_type="execute_command",
                    params={"command": f"python -m pip install {pip_name}"},
                    priority=3,
                ),
            ]
            
        elif error_type == ErrorType.PIP_INSTALL:
            if original_params and "command" in original_params:
                cmd = original_params["command"]
                # Extract package name from pip install command
                match = re.search(r"pip\d?\s+install\s+([^\s]+)", cmd)
                if match:
                    package = match.group(1)
                    strategies = [
                        RecoveryAction(
                            description=f"Try pip install with --user",
                            action_type="execute_command",
                            params={"command": f"pip install --user {package}"},
                            priority=1,
                        ),
                        RecoveryAction(
                            description=f"Try pip install with --break-system-packages",
                            action_type="execute_command",
                            params={"command": f"pip install {package} --break-system-packages"},
                            priority=2,
                        ),
                        RecoveryAction(
                            description=f"Update pip and retry",
                            action_type="execute_command",
                            params={"command": f"pip install --upgrade pip && pip install {package}"},
                            priority=3,
                        ),
                    ]
                    
        elif error_type == ErrorType.FILE_NOT_FOUND:
            if original_params:
                file_path = original_params.get("file_path", extracted_value)
                if file_path:
                    # Check if it's a directory issue
                    import os
                    parent_dir = os.path.dirname(file_path) if file_path else ""
                    if parent_dir:
                        strategies = [
                            RecoveryAction(
                                description=f"Create parent directory {parent_dir}",
                                action_type="execute_command",
                                params={"command": f"mkdir -p {parent_dir}"},
                                priority=1,
                            ),
                        ]
                        
        elif error_type == ErrorType.COMMAND_NOT_FOUND:
            command = extracted_value or ""
            # Common command -> package mappings
            package_map = {
                "wget": "wget",
                "curl": "curl",
                "git": "git",
                "zip": "zip",
                "unzip": "unzip",
                "jq": "jq",
                "ffmpeg": "ffmpeg",
                "convert": "imagemagick",
                "pandoc": "pandoc",
            }
            
            if command in package_map:
                package = package_map[command]
                strategies = [
                    RecoveryAction(
                        description=f"Install {package} via apt-get",
                        action_type="execute_command",
                        params={"command": f"apt-get update && apt-get install -y {package}"},
                        priority=1,
                    ),
                ]
            else:
                strategies = [
                    RecoveryAction(
                        description=f"Try to install {command} via apt-get",
                        action_type="execute_command",
                        params={"command": f"apt-get update && apt-get install -y {command}"},
                        priority=1,
                    ),
                ]
                
        elif error_type == ErrorType.PERMISSION_DENIED:
            if original_params and "command" in original_params:
                cmd = original_params["command"]
                # Don't add sudo blindly, but suggest chmod for files
                if "file_path" in original_params:
                    file_path = original_params["file_path"]
                    strategies = [
                        RecoveryAction(
                            description=f"Fix permissions for {file_path}",
                            action_type="execute_command",
                            params={"command": f"chmod 644 {file_path}"},
                            priority=1,
                        ),
                    ]
                    
        elif error_type == ErrorType.SYNTAX_ERROR:
            # For syntax errors, we can't auto-fix, but we can suggest
            strategies = [
                RecoveryAction(
                    description="Syntax error detected - need to fix the code",
                    action_type="notify_user",
                    params={"message": "The code has a syntax error. Please review and fix."},
                    priority=1,
                ),
            ]
            
        elif error_type == ErrorType.NETWORK_ERROR:
            strategies = [
                RecoveryAction(
                    description="Retry after brief delay (network issue)",
                    action_type="retry_with_delay",
                    params={"delay": 2},
                    priority=1,
                ),
            ]
            
        elif error_type == ErrorType.TIMEOUT:
            # Increase timeout or split task
            strategies = [
                RecoveryAction(
                    description="Task timed out - try with longer timeout",
                    action_type="retry_with_timeout",
                    params={"timeout": 60},
                    priority=1,
                ),
            ]
        
        return strategies


class RecoveryManager:
    """Manages error recovery for the agent."""
    
    def __init__(self, max_retries: int = 3):
        """Initialize recovery manager.
        
        Args:
            max_retries: Maximum number of recovery attempts per error.
        """
        self.max_retries = max_retries
        self.recovery_history: List[RecoveryResult] = []
        self._current_retries: Dict[str, int] = {}  # error_hash -> retry count
        
    def _hash_error(self, error: str, action: str) -> str:
        """Create a hash for an error to track retries."""
        # Normalize the error message
        normalized = re.sub(r'\d+', 'N', error)  # Replace numbers
        normalized = re.sub(r'0x[a-fA-F0-9]+', 'ADDR', normalized)  # Replace addresses
        return f"{action}:{hash(normalized)}"
        
    def analyze_error(
        self,
        error_message: str,
        action: str,
        params: Optional[Dict] = None,
    ) -> Optional[RecoveryAction]:
        """Analyze an error and return a recovery action if possible.
        
        Args:
            error_message: The error message/observation.
            action: The action that failed (e.g., "execute_command").
            params: The parameters of the failed action.
            
        Returns:
            RecoveryAction to try, or None if no recovery possible.
        """
        # Check if we've exceeded retries for this error
        error_hash = self._hash_error(error_message, action)
        current_retries = self._current_retries.get(error_hash, 0)
        
        if current_retries >= self.max_retries:
            return None
            
        # Detect error type
        error_type, extracted = ErrorPatterns.detect_error_type(error_message)
        
        if error_type == ErrorType.UNKNOWN:
            return None
            
        # Get recovery strategies
        strategies = RecoveryStrategies.get_strategies(
            error_type=error_type,
            extracted_value=extracted,
            original_action=action,
            original_params=params,
        )
        
        if not strategies:
            return None
            
        # Return the next strategy to try
        strategy_index = min(current_retries, len(strategies) - 1)
        recovery_action = strategies[strategy_index]
        
        # Increment retry count
        self._current_retries[error_hash] = current_retries + 1
        
        # Record in history
        self.recovery_history.append(RecoveryResult(
            success=False,  # Will be updated after execution
            error_type=error_type,
            original_error=error_message,
            recovery_action=recovery_action,
            attempts=current_retries + 1,
        ))
        
        return recovery_action
        
    def record_success(self, error_hash: str):
        """Record a successful recovery."""
        if self.recovery_history:
            self.recovery_history[-1].success = True
        # Reset retry count on success
        if error_hash in self._current_retries:
            del self._current_retries[error_hash]
            
    def reset(self):
        """Reset retry counts (e.g., for new task)."""
        self._current_retries.clear()
        
    def get_recovery_summary(self) -> Dict[str, Any]:
        """Get a summary of recovery attempts."""
        total = len(self.recovery_history)
        successful = sum(1 for r in self.recovery_history if r.success)
        
        by_type: Dict[str, int] = {}
        for r in self.recovery_history:
            key = r.error_type.value
            by_type[key] = by_type.get(key, 0) + 1
            
        return {
            "total_attempts": total,
            "successful": successful,
            "by_error_type": by_type,
        }
