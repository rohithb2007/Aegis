import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class SupervisorVerdict(str, Enum):
    ALIGNED = "ALIGNED"
    QUESTIONABLE = "QUESTIONABLE"
    SUSPICIOUS = "SUSPICIOUS"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


class SupervisorAlignment(str, Enum):
    ALIGNED = "ALIGNED"
    PARTIALLY_ALIGNED = "PARTIALLY_ALIGNED"
    NOT_ALIGNED = "NOT_ALIGNED"
    UNKNOWN = "UNKNOWN"


class RecommendedAction(str, Enum):
    NO_CONCERN = "NO_CONCERN"
    REVIEW = "REVIEW"
    ESCALATE = "ESCALATE"
    UNKNOWN = "UNKNOWN"


@dataclass
class SupervisorAssessment:
    verdict: SupervisorVerdict
    confidence: str
    alignment: SupervisorAlignment
    explanation: str
    concerns: List[str] = field(default_factory=list)
    recommended_action: RecommendedAction = RecommendedAction.UNKNOWN
    model: str = "mock-supervisor"
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    command: Optional[str] = None
    safety_classification: Optional[str] = None
    safety_score: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value if isinstance(self.verdict, SupervisorVerdict) else str(self.verdict),
            "confidence": self.confidence,
            "alignment": self.alignment.value if isinstance(self.alignment, SupervisorAlignment) else str(self.alignment),
            "explanation": self.explanation,
            "concerns": self.concerns,
            "recommended_action": self.recommended_action.value if isinstance(self.recommended_action, RecommendedAction) else str(self.recommended_action),
            "model": self.model,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "command": self.command,
            "safety_classification": self.safety_classification,
            "safety_score": self.safety_score,
        }
