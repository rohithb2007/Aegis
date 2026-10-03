import os
import json
import uuid
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from ai_supervisor.sanitizer import ContextSanitizer


@dataclass
class AuditRecord:
    record_id: str
    timestamp: str
    command: str
    v03_risk: str
    risk_score: int
    capabilities: List[str]
    final_policy_decision: str
    policy_reasons: List[str]
    event_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    v04_verdict: Optional[str] = None
    v04_confidence: Optional[str] = None
    v05_route: Optional[str] = None
    approval_status: Optional[str] = None
    policy_version: str = "0.6.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "command": self.command,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "v03_risk": self.v03_risk,
            "risk_score": self.risk_score,
            "capabilities": self.capabilities,
            "v04_verdict": self.v04_verdict,
            "v04_confidence": self.v04_confidence,
            "v05_route": self.v05_route,
            "final_policy_decision": self.final_policy_decision,
            "policy_reasons": self.policy_reasons,
            "approval_status": self.approval_status,
            "policy_version": self.policy_version,
        }


class AuditLogger:
    """Secret-redacted audit logger for Aegis V0.6 policy decisions."""

    def __init__(self, log_filepath: Optional[str] = None, max_in_memory: int = 200):
        self._lock = threading.Lock()
        self.log_filepath = log_filepath
        self.max_in_memory = max_in_memory
        self.records: List[AuditRecord] = []
        self.sanitizer = ContextSanitizer()

    def log(
        self,
        command: str,
        v03_risk: str,
        risk_score: int,
        capabilities: List[str],
        final_policy_decision: str,
        policy_reasons: List[str],
        event_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        v04_verdict: Optional[str] = None,
        v04_confidence: Optional[str] = None,
        v05_route: Optional[str] = None,
        approval_status: Optional[str] = None,
        policy_version: str = "0.6.0",
    ) -> AuditRecord:
        now_iso = datetime.now(timezone.utc).isoformat()
        rec_id = f"aud-{uuid.uuid4().hex[:8]}"

        # Always redact raw secrets from command string prior to recording
        sanitized_command = self.sanitizer.redact_secrets(command or "")

        # Also sanitize reasons just in case
        sanitized_reasons = [self.sanitizer.redact_secrets(r or "") for r in policy_reasons]

        record = AuditRecord(
            record_id=rec_id,
            timestamp=now_iso,
            event_id=event_id,
            command=sanitized_command,
            session_id=session_id,
            task_id=task_id,
            v03_risk=v03_risk,
            risk_score=risk_score,
            capabilities=capabilities,
            v04_verdict=v04_verdict,
            v04_confidence=v04_confidence,
            v05_route=v05_route,
            final_policy_decision=final_policy_decision,
            policy_reasons=sanitized_reasons,
            approval_status=approval_status,
            policy_version=policy_version,
        )

        with self._lock:
            self.records.append(record)
            if len(self.records) > self.max_in_memory:
                self.records = self.records[-self.max_in_memory:]

            if self.log_filepath:
                try:
                    with open(self.log_filepath, "a", encoding="utf-8") as f:
                        f.write(json.dumps(record.to_dict()) + "\n")
                except Exception:
                    pass  # Audit logging should never crash the main loop

        return record

    def get_records(self) -> List[AuditRecord]:
        with self._lock:
            return list(self.records)

    def read_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            recs = self.records[-limit:]
            return [r.to_dict() for r in reversed(recs)]

    def clear(self) -> None:
        with self._lock:
            self.records.clear()

