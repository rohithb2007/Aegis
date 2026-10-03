import os
import re
from typing import Optional, Tuple, List
from .models import WorkspaceBoundary, GatewayStatus, ProtectedContext
from ai_supervisor.sanitizer import ContextSanitizer


class ProtectedGateway:
    """Aegis V0.8 Workspace Protection Gateway evaluating boundary constraints."""

    def __init__(self, workspace_boundary: Optional[WorkspaceBoundary] = None):
        self.boundary = workspace_boundary or WorkspaceBoundary(workspace_root=os.getcwd())
        self.sanitizer = ContextSanitizer()

    def validate_command_scope(
        self, command: str, context: Optional[ProtectedContext] = None
    ) -> Tuple[bool, List[str]]:
        """Analyzes proposed command for workspace boundary escapes or unauthorized path traversals."""
        cmd_lower = (command or "").lower()
        reasons: List[str] = []

        # 1. Root or System Destructive/Escape Regex Check
        if re.search(r'rm\s+-rf\s+[\/\*]|del\s+/s\s+c:\\windows|rd\s+/s\s+/q\s+c:\\', cmd_lower):
            reasons.append("Command targets root or system directory outside workspace boundary.")
            return False, reasons

        # 2. Absolute Path System Directory Check
        if re.search(r'(\/etc\/|\/var\/root|c:\\windows|c:\\system32|\\\\.+)', cmd_lower):
            reasons.append("Command references system directory or network share outside workspace boundary.")
            return False, reasons

        # 3. Directory Traversal Check out of Workspace Root
        if "../" in cmd_lower or "..\\" in cmd_lower:
            # Check if traversal escapes the root
            work_root = context.workspace_root if context else self.boundary.workspace_root
            cwd = context.cwd if context else os.getcwd()
            # Extract potential path targets
            tokens = cmd_lower.split()
            for tok in tokens:
                if ".." in tok:
                    candidate_path = os.path.abspath(os.path.join(cwd, tok))
                    if not self.boundary.is_path_inside(candidate_path):
                        reasons.append(f"Directory traversal path '{tok}' escapes protected workspace boundary.")
                        return False, reasons

        return True, []
