import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


class EnforcementStatus(str, Enum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    ALLOWED = "ALLOWED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    DENIED = "DENIED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    SIMULATED = "SIMULATED"
    NOT_CONNECTED = "NOT_CONNECTED_TO_PRE_EXECUTION_HOOK"


class ExecutionMode(str, Enum):
    SIMULATION = "SIMULATION"
    CONTROLLED = "CONTROLLED"
    LIVE = "LIVE"


@dataclass
class EnforcementRequest:
    enforcement_id: str
    command: str
    event_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    policy_decision: str = "UNKNOWN"
    policy_severity: str = "INFORMATIONAL"
    v03_risk: Optional[str] = None
    approval_id: Optional[str] = None
    execution_mode: ExecutionMode = ExecutionMode.SIMULATION
    timestamp: Optional[str] = None

    @classmethod
    def create(
        cls,
        command: str,
        policy_decision: str = "UNKNOWN",
        policy_severity: str = "INFORMATIONAL",
        v03_risk: Optional[str] = None,
        approval_id: Optional[str] = None,
        execution_mode: ExecutionMode = ExecutionMode.SIMULATION,
        event_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        enforcement_id: Optional[str] = None,
    ) -> "EnforcementRequest":
        now_iso = datetime.now(timezone.utc).isoformat()
        enf_id = enforcement_id or f"enf-{uuid.uuid4().hex[:8]}"
        return cls(
            enforcement_id=enf_id,
            command=command,
            event_id=event_id,
            session_id=session_id,
            task_id=task_id,
            policy_decision=policy_decision,
            policy_severity=policy_severity,
            v03_risk=v03_risk,
            approval_id=approval_id,
            execution_mode=execution_mode,
            timestamp=now_iso,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enforcement_id": self.enforcement_id,
            "command": self.command,
            "event_id": self.event_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "policy_decision": self.policy_decision,
            "policy_severity": self.policy_severity,
            "v03_risk": self.v03_risk,
            "approval_id": self.approval_id,
            "execution_mode": self.execution_mode.value if isinstance(self.execution_mode, ExecutionMode) else str(self.execution_mode),
            "timestamp": self.timestamp,
        }
