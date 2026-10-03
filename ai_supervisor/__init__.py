"""
Aegis AI Supervisor Package — Advisory Contextual Reasoning & Intelligent Model Router Layer
"""

from .models import (
    SupervisorVerdict, SupervisorAlignment, RecommendedAction, SupervisorAssessment
)
from .sanitizer import ContextSanitizer
from .prompt import PromptBuilder
from .providers import AIProvider, MockProvider, OpenAIProvider, get_provider_from_env
from .supervisor import AISupervisor
from .routing_models import (
    RouteClass, RoutingPriority, SensitivityLevel, RoutingDecision, RoutingMetrics
)
from .routing_rules import (
    ComplexityScorer, UncertaintyScorer, SensitivityMultiplier
)
from .router import ModelRouter

__all__ = [
    "SupervisorVerdict",
    "SupervisorAlignment",
    "RecommendedAction",
    "SupervisorAssessment",
    "ContextSanitizer",
    "PromptBuilder",
    "AIProvider",
    "MockProvider",
    "OpenAIProvider",
    "get_provider_from_env",
    "AISupervisor",
    "RouteClass",
    "RoutingPriority",
    "SensitivityLevel",
    "RoutingDecision",
    "RoutingMetrics",
    "ComplexityScorer",
    "UncertaintyScorer",
    "SensitivityMultiplier",
    "ModelRouter",
]
