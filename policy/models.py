from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class PolicySeverity(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class PolicyReason:
    rule_id: str
    severity: PolicySeverity
    title: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value if isinstance(self.severity, PolicySeverity) else str(self.severity),
            "title": self.title,
            "explanation": self.explanation,
        }


@dataclass
class PolicyAssessment:
    decision: PolicyDecision
    severity: PolicySeverity
    reasons: List[PolicyReason] = field(default_factory=list)
    risk_score: int = 0
    ai_verdict: Optional[str] = None
    routing_decision: Optional[str] = None
    confidence: str = "HIGH"
    policy_version: str = "0.6.0"
    timestamp: Optional[str] = None
    command: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    approval_request_id: Optional[str] = None
    v03_risk: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value if isinstance(self.decision, PolicyDecision) else str(self.decision),
            "severity": self.severity.value if isinstance(self.severity, PolicySeverity) else str(self.severity),
            "reasons": [r.to_dict() for r in self.reasons],
            "risk_score": self.risk_score,
            "v03_risk": self.v03_risk,
            "ai_verdict": self.ai_verdict,
            "routing_decision": self.routing_decision,
            "confidence": self.confidence,
            "policy_version": self.policy_version,
            "timestamp": self.timestamp,
            "command": self.command,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "approval_request_id": self.approval_request_id,
        }

    def render_console(self) -> str:
        primary_reason = self.reasons[0].explanation if self.reasons else "No explicit reason provided."
        
        approval_str = "N/A"
        if self.approval_request_id:
            approval_str = f"PENDING (ID: {self.approval_request_id})"
        elif self.decision == PolicyDecision.REVIEW:
            approval_str = "PENDING"
        elif self.decision == PolicyDecision.BLOCK:
            approval_str = "NOT AVAILABLE"

        lines = [
            "====================================",
            "        AEGIS POLICY ENGINE         ",
            "====================================",
            f"Command:\n  {self.command or 'N/A'}",
            f"\nDeterministic Risk:\n  {self.v03_risk or 'UNKNOWN'}",
            f"\nRisk Score:\n  {self.risk_score}",
            f"\nAI Verdict:\n  {self.ai_verdict or 'N/A'}",
            f"\nModel Route:\n  {self.routing_decision or 'N/A'}",
            f"\nPolicy:\n  {self.decision.value if isinstance(self.decision, PolicyDecision) else self.decision}",
            f"\nSeverity:\n  {self.severity.value if isinstance(self.severity, PolicySeverity) else self.severity}",
            f"\nReason:\n  {primary_reason}",
            f"\nApproval:\n  {approval_str}",
            "\nEnforcement:\n  NOT IMPLEMENTED",
            "====================================",
        ]
        return "\n".join(lines)
