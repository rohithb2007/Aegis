import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class SafetyClassification(str, Enum):
    SAFE = "SAFE"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class SafetyAction(str, Enum):
    OBSERVE = "OBSERVE_ONLY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RESTRICTED = "RESTRICTED"


class CapabilityType(str, Enum):
    READ_FILESYSTEM = "READ_FILESYSTEM"
    WRITE_FILESYSTEM = "WRITE_FILESYSTEM"
    DELETE_FILESYSTEM = "DELETE_FILESYSTEM"
    EXECUTE_PROCESS = "EXECUTE_PROCESS"
    NETWORK_ACCESS = "NETWORK_ACCESS"
    NETWORK_LISTENER = "NETWORK_LISTENER"
    PACKAGE_INSTALLATION = "PACKAGE_INSTALLATION"
    GIT_LOCAL = "GIT_LOCAL"
    GIT_REMOTE = "GIT_REMOTE"
    REMOTE_STATE_CHANGE = "REMOTE_STATE_CHANGE"
    DATABASE_READ = "DATABASE_READ"
    DATABASE_WRITE = "DATABASE_WRITE"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    ENVIRONMENT_ACCESS = "ENVIRONMENT_ACCESS"
    CREDENTIAL_ACCESS = "CREDENTIAL_ACCESS"
    ARCHIVE_OPERATION = "ARCHIVE_OPERATION"
    SYSTEM_CONFIGURATION = "SYSTEM_CONFIGURATION"
    UNKNOWN_CAPABILITY = "UNKNOWN_CAPABILITY"


class Reversibility(str, Enum):
    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    DIFFICULT_TO_REVERSE = "DIFFICULT_TO_REVERSE"
    IRREVERSIBLE = "IRREVERSIBLE"
    UNKNOWN = "UNKNOWN"


class Scope(str, Enum):
    INSIDE_PROJECT = "INSIDE_PROJECT"
    OUTSIDE_PROJECT = "OUTSIDE_PROJECT"
    UNKNOWN = "UNKNOWN"


@dataclass
class SafetyAssessment:
    command: str
    classification: SafetyClassification
    action: SafetyAction
    score: int
    reasons: List[str] = field(default_factory=list)
    capabilities: List[CapabilityType] = field(default_factory=list)
    reversibility: Reversibility = Reversibility.UNKNOWN
    scope: Scope = Scope.UNKNOWN
    confidence: str = "HIGH"
    matched_rules: List[str] = field(default_factory=list)
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "classification": self.classification.value if isinstance(self.classification, SafetyClassification) else str(self.classification),
            "action": self.action.value if isinstance(self.action, SafetyAction) else str(self.action),
            "score": self.score,
            "reasons": self.reasons,
            "capabilities": [c.value if isinstance(c, CapabilityType) else str(c) for c in self.capabilities],
            "reversibility": self.reversibility.value if isinstance(self.reversibility, Reversibility) else str(self.reversibility),
            "scope": self.scope.value if isinstance(self.scope, Scope) else str(self.scope),
            "confidence": self.confidence,
            "matched_rules": self.matched_rules,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "task_id": self.task_id,
        }
