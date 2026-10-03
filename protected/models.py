import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


class GatewayStatus(str, Enum):
    PASSTHROUGH = "PASSTHROUGH"
    EVALUATING = "EVALUATING"
    PERMITTED = "PERMITTED"
    PAUSED_FOR_APPROVAL = "PAUSED_FOR_APPROVAL"
    REJECTED_POLICY = "REJECTED_POLICY"
    REJECTED_SCOPE = "REJECTED_SCOPE"
    FAILED_GATEWAY = "FAILED_GATEWAY"


@dataclass
class WorkspaceBoundary:
    workspace_root: str
    allowed_dirs: List[str] = field(default_factory=list)
    strict_scope_check: bool = True

    def __post_init__(self):
        self.workspace_root = os.path.abspath(self.workspace_root)
        self.allowed_dirs = [os.path.abspath(d) for d in self.allowed_dirs]

    def is_path_inside(self, target_path: str) -> bool:
        """Determines if a file/directory path resides inside the protected workspace boundary."""
        if not target_path:
            return True
        try:
            abs_target = os.path.abspath(target_path)
            # Check relative path to workspace root
            rel_path = os.path.relpath(abs_target, self.workspace_root)
            if not rel_path.startswith("..") and not os.path.isabs(rel_path):
                return True
            for allowed in self.allowed_dirs:
                rel_allowed = os.path.relpath(abs_target, allowed)
                if not rel_allowed.startswith("..") and not os.path.isabs(rel_allowed):
                    return True
            return False
        except Exception:
            return False


@dataclass
class ProtectedContext:
    workspace_root: str = field(default_factory=lambda: os.getcwd())
    cwd: str = field(default_factory=lambda: os.getcwd())
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    user_goal: Optional[str] = None
    workflow_phase: Optional[str] = None
    recent_files: List[str] = field(default_factory=list)
    recent_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_root": self.workspace_root,
            "cwd": self.cwd,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "user_goal": self.user_goal,
            "workflow_phase": self.workflow_phase,
            "recent_files": self.recent_files,
            "recent_errors": self.recent_errors,
        }


@dataclass
class ProtectedResponse:
    gateway_status: GatewayStatus
    command: str
    policy_decision: str = "UNKNOWN"
    enforcement_status: str = "UNKNOWN"
    approval_id: Optional[str] = None
    approval_status: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    reasons: List[str] = field(default_factory=list)
    explanation: str = ""
    timestamp: Optional[str] = None
    event_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    enforcement_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gateway_status": self.gateway_status.value if isinstance(self.gateway_status, GatewayStatus) else str(self.gateway_status),
            "command": self.command,
            "policy_decision": self.policy_decision,
            "enforcement_status": self.enforcement_status,
            "approval_id": self.approval_id,
            "approval_status": self.approval_status,
            "execution_result": self.execution_result,
            "reasons": self.reasons,
            "explanation": self.explanation,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "enforcement_id": self.enforcement_id,
        }

    def render_console(self) -> str:
        lines = [
            "====================================",
            "   AEGIS PROTECTED WORKSPACE PROXY  ",
            "====================================",
            f"Command:\n  {self.command}",
            f"\nGateway Status:\n  {self.gateway_status.value if isinstance(self.gateway_status, GatewayStatus) else self.gateway_status}",
            f"\nPolicy Decision:\n  {self.policy_decision}",
            f"\nEnforcement Status:\n  {self.enforcement_status}",
            f"\nApproval Status:\n  {self.approval_status or 'N/A'}",
            f"\nExplanation:\n  {self.explanation}",
            "\nIntegration Boundary Notice:\n  Pre-execution boundary active for CommandProxy submissions.",
            "====================================",
        ]
        return "\n".join(lines)
