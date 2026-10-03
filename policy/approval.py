import re
import uuid
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


def normalize_command(command: str) -> str:
    """Normalizes a command string for exact identity binding verification.
    
    Rules:
    1. Strip leading and trailing whitespace.
    2. Normalize multiple internal spaces/tabs to a single space.
    3. Normalize backslashes '\\' to forward slashes '/' in path arguments for cross-platform consistency.
    4. Lowercase the primary executable/cmdlet (first token) for Windows case-insensitivity.
    """
    if not command:
        return ""
    
    cmd = command.strip()
    cmd = re.sub(r'\s+', ' ', cmd)
    
    # Split first token (executable) and remaining command
    parts = cmd.split(' ', 1)
    exe = parts[0].lower()
    
    if len(parts) > 1:
        rest = parts[1]
        # Normalize backslashes in paths while preserving quoted strings
        rest = rest.replace('\\', '/')
        cmd = f"{exe} {rest}"
    else:
        cmd = exe
        
    return cmd


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


@dataclass
class ApprovalRequest:
    request_id: str
    command: str
    risk_classification: str
    risk_score: int
    capabilities: List[str]
    ai_verdict: Optional[str]
    explanation: str
    policy_reasons: List[Dict[str, Any]]
    created_at: str
    normalized_command: str = field(default="")
    project_workspace: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    workflow_phase: Optional[str] = None
    reason_for_review: Optional[str] = None
    policy_decision: str = "REVIEW"
    expires_at: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None

    def __post_init__(self):
        if not self.normalized_command:
            self.normalized_command = normalize_command(self.command)
        if not self.reason_for_review:
            self.reason_for_review = self.explanation

    def check_expired(self) -> bool:
        """Check if pending request has passed its expiration timestamp."""
        if self.status == ApprovalStatus.PENDING and self.expires_at:
            try:
                exp_dt = datetime.fromisoformat(self.expires_at)
                now_dt = datetime.now(timezone.utc)
                if now_dt > exp_dt:
                    self.status = ApprovalStatus.EXPIRED
                    return True
            except Exception:
                pass
        return self.status == ApprovalStatus.EXPIRED

    def to_dict(self) -> Dict[str, Any]:
        self.check_expired()
        return {
            "request_id": self.request_id,
            "command": self.command,
            "normalized_command": self.normalized_command,
            "risk_classification": self.risk_classification,
            "risk_score": self.risk_score,
            "capabilities": self.capabilities,
            "ai_verdict": self.ai_verdict,
            "ai_assessment": self.ai_verdict,
            "explanation": self.explanation,
            "reason_for_review": self.reason_for_review or self.explanation,
            "policy_reasons": self.policy_reasons,
            "project_workspace": self.project_workspace,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "workflow_phase": self.workflow_phase,
            "policy_decision": self.policy_decision,
            "created_at": self.created_at,
            "timestamp": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status.value if isinstance(self.status, ApprovalStatus) else str(self.status),
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
        }


class ApprovalManager:
    """Thread-safe in-memory Approval Manager establishing human approval state machine."""

    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, ApprovalRequest] = {}

    def create_request(
        self,
        command: str,
        risk_classification: str,
        risk_score: int,
        capabilities: List[str],
        ai_verdict: Optional[str],
        explanation: str,
        policy_reasons: List[Dict[str, Any]],
        expires_at: Optional[str] = None,
        request_id: Optional[str] = None,
        project_workspace: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        workflow_phase: Optional[str] = None,
        reason_for_review: Optional[str] = None,
        policy_decision: str = "REVIEW",
    ) -> ApprovalRequest:
        now_iso = datetime.now(timezone.utc).isoformat()
        req_id = request_id or f"req-{uuid.uuid4().hex[:8]}"

        request = ApprovalRequest(
            request_id=req_id,
            command=command,
            normalized_command=normalize_command(command),
            risk_classification=risk_classification,
            risk_score=risk_score,
            capabilities=capabilities,
            ai_verdict=ai_verdict,
            explanation=explanation,
            policy_reasons=policy_reasons,
            created_at=now_iso,
            expires_at=expires_at,
            status=ApprovalStatus.PENDING,
            project_workspace=project_workspace,
            session_id=session_id,
            task_id=task_id,
            workflow_phase=workflow_phase,
            reason_for_review=reason_for_review or explanation,
            policy_decision=policy_decision,
        )

        with self._lock:
            self._requests[req_id] = request

        return request

    def approve(self, request_id: str, decided_by: str = "user") -> Optional[ApprovalRequest]:
        """Transitions request PENDING -> APPROVED. Idempotent for APPROVED; strictly blocks invalid transitions (e.g. DENIED -> APPROVED)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                return None
            req.check_expired()
            if req.status != ApprovalStatus.PENDING:
                if req.status == ApprovalStatus.APPROVED:
                    return req
                return None
            req.status = ApprovalStatus.APPROVED
            req.decided_at = now_iso
            req.decided_by = decided_by
            return req

    def deny(self, request_id: str, decided_by: str = "user") -> Optional[ApprovalRequest]:
        """Transitions request PENDING -> DENIED. Idempotent for DENIED; strictly blocks invalid transitions."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                return None
            req.check_expired()
            if req.status != ApprovalStatus.PENDING:
                if req.status == ApprovalStatus.DENIED:
                    return req
                return None
            req.status = ApprovalStatus.DENIED
            req.decided_at = now_iso
            req.decided_by = decided_by
            return req

    def cancel(self, request_id: str) -> Optional[ApprovalRequest]:
        """Transitions request PENDING -> CANCELLED."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                return None
            req.check_expired()
            if req.status != ApprovalStatus.PENDING:
                if req.status == ApprovalStatus.CANCELLED:
                    return req
                return None
            req.status = ApprovalStatus.CANCELLED
            req.decided_at = now_iso
            return req

    def mark_expired(self, request_id: str) -> Optional[ApprovalRequest]:
        """Transitions request PENDING -> EXPIRED."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            req = self._requests.get(request_id)
            if not req:
                return None
            if req.status != ApprovalStatus.PENDING:
                if req.status == ApprovalStatus.EXPIRED:
                    return req
                return None
            req.status = ApprovalStatus.EXPIRED
            req.decided_at = now_iso
            return req

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
            req = self._requests.get(request_id)
            if req:
                req.check_expired()
            return req

    def find_approved_request(
        self,
        command: str,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        project_workspace: Optional[str] = None,
    ) -> Optional[ApprovalRequest]:
        """Verifies exact command identity, normalization, session, task, workspace, and APPROVED status."""
        norm_cmd = normalize_command(command)
        with self._lock:
            if request_id:
                req = self._requests.get(request_id)
                if not req:
                    return None
                req.check_expired()
                if req.status != ApprovalStatus.APPROVED:
                    return None
                if req.normalized_command != norm_cmd:
                    # Command materially changed after approval => reject!
                    return None
                return req

            # Search by normalized command identity and session context
            for req in self._requests.values():
                req.check_expired()
                if req.status == ApprovalStatus.APPROVED and req.normalized_command == norm_cmd:
                    if session_id and req.session_id and req.session_id != session_id:
                        continue
                    if task_id and req.task_id and req.task_id != task_id:
                        continue
                    if project_workspace and req.project_workspace and req.project_workspace != project_workspace:
                        continue
                    return req
            return None

    def list_requests(self, status: Optional[ApprovalStatus] = None) -> List[ApprovalRequest]:
        with self._lock:
            for req in self._requests.values():
                req.check_expired()
            if status is None:
                return list(self._requests.values())
            status_val = status.value if isinstance(status, ApprovalStatus) else str(status)
            return [
                req for req in self._requests.values()
                if (req.status.value if isinstance(req.status, ApprovalStatus) else str(req.status)) == status_val
            ]

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
