from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class RouteClass(str, Enum):
    NO_AI = "NO_AI"
    FAST_AI = "FAST_AI"
    STRONG_AI = "STRONG_AI"
    FALLBACK_AI = "FALLBACK_AI"


class RoutingPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SensitivityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RoutingDecision:
    route: RouteClass
    reason: str
    provider: Optional[str] = None
    model: Optional[str] = None
    estimated_priority: RoutingPriority = RoutingPriority.LOW
    complexity_score: int = 0
    uncertainty_score: int = 0
    sensitivity_level: SensitivityLevel = SensitivityLevel.LOW
    safety_classification: str = "SAFE"
    safety_score: int = 0
    ai_call_avoided: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route.value if isinstance(self.route, RouteClass) else str(self.route),
            "reason": self.reason,
            "provider": self.provider,
            "model": self.model,
            "estimated_priority": (
                self.estimated_priority.value
                if isinstance(self.estimated_priority, RoutingPriority)
                else str(self.estimated_priority)
            ),
            "complexity_score": self.complexity_score,
            "uncertainty_score": self.uncertainty_score,
            "sensitivity_level": (
                self.sensitivity_level.value
                if isinstance(self.sensitivity_level, SensitivityLevel)
                else str(self.sensitivity_level)
            ),
            "safety_classification": self.safety_classification,
            "safety_score": self.safety_score,
            "ai_call_avoided": self.ai_call_avoided,
        }

    def render_console(self) -> str:
        lines = [
            "=" * 50,
            "AEGIS MODEL ROUTER (V0.5)",
            "=" * 50,
            f"Risk:                   {self.safety_classification}",
            f"Risk Score:             {self.safety_score}",
            f"Complexity Score:       {self.complexity_score}",
            f"Uncertainty Score:      {self.uncertainty_score}",
            f"Sensitivity Level:      {self.sensitivity_level.value if isinstance(self.sensitivity_level, SensitivityLevel) else self.sensitivity_level}",
            f"Route:                  {self.route.value if isinstance(self.route, RouteClass) else self.route}",
            f"Estimated Priority:     {self.estimated_priority.value if isinstance(self.estimated_priority, RoutingPriority) else self.estimated_priority}",
            f"Provider:               {self.provider or 'N/A'}",
            f"Model:                  {self.model or 'N/A'}",
            f"AI Call Avoided:        {self.ai_call_avoided}",
            f"Reason:                 {self.reason}",
            "=" * 50,
        ]
        return "\n".join(lines)


@dataclass
class RoutingMetrics:
    total_actions_analyzed: int = 0
    no_ai_count: int = 0
    fast_ai_count: int = 0
    strong_ai_count: int = 0
    fallback_ai_count: int = 0
    ai_calls_avoided: int = 0
    routing_escalations: int = 0

    def record_decision(self, decision: RoutingDecision, escalated: bool = False) -> None:
        self.total_actions_analyzed += 1
        if decision.route == RouteClass.NO_AI:
            self.no_ai_count += 1
            self.ai_calls_avoided += 1
        elif decision.route == RouteClass.FAST_AI:
            self.fast_ai_count += 1
        elif decision.route == RouteClass.STRONG_AI:
            self.strong_ai_count += 1
        elif decision.route == RouteClass.FALLBACK_AI:
            self.fallback_ai_count += 1

        if escalated:
            self.routing_escalations += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_actions_analyzed": self.total_actions_analyzed,
            "no_ai_count": self.no_ai_count,
            "fast_ai_count": self.fast_ai_count,
            "strong_ai_count": self.strong_ai_count,
            "fallback_ai_count": self.fallback_ai_count,
            "ai_calls_avoided": self.ai_calls_avoided,
            "routing_escalations": self.routing_escalations,
        }
