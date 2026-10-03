import os
from typing import Optional, Dict, Any
from safety.models import SafetyAssessment, SafetyClassification, CapabilityType
from supervisor.session import SessionState
from .routing_models import (
    RouteClass, RoutingPriority, SensitivityLevel,
    RoutingDecision, RoutingMetrics
)
from .routing_rules import ComplexityScorer, UncertaintyScorer, SensitivityMultiplier


class ModelRouter:
    """Deterministic Intelligent Model Router for Aegis V0.5."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.metrics = RoutingMetrics()

    def _get_provider_config(self, route: RouteClass) -> tuple[Optional[str], Optional[str]]:
        """Resolve provider and model for a given route class from env / config."""
        if route == RouteClass.NO_AI:
            return None, None

        if route == RouteClass.FAST_AI:
            provider = os.getenv("AEGIS_FAST_PROVIDER") or self.config.get("fast_provider") or "openai"
            model = os.getenv("AEGIS_FAST_MODEL") or self.config.get("fast_model") or "gpt-4o-mini"
            return provider, model

        if route == RouteClass.STRONG_AI:
            provider = os.getenv("AEGIS_STRONG_PROVIDER") or self.config.get("strong_provider") or "openai"
            model = os.getenv("AEGIS_STRONG_MODEL") or self.config.get("strong_model") or "gpt-4o"
            return provider, model

        # FALLBACK_AI
        provider = os.getenv("AEGIS_FALLBACK_PROVIDER") or self.config.get("fallback_provider") or "mock"
        model = os.getenv("AEGIS_FALLBACK_MODEL") or self.config.get("fallback_model") or "mock-supervisor"
        return provider, model

    def route(
        self,
        command: str,
        safety_assessment: Optional[SafetyAssessment] = None,
        session_state: Optional[SessionState] = None
    ) -> RoutingDecision:
        """Determines the optimal RouteClass, provider, model, and reasoning depth for a command."""
        # 1. Gather baseline scores
        complexity = ComplexityScorer.calculate(command, safety_assessment, session_state)
        uncertainty = UncertaintyScorer.calculate(command, safety_assessment, session_state)
        sensitivity_level, sensitivity_score = SensitivityMultiplier.evaluate(command, safety_assessment)

        risk_class = (
            safety_assessment.classification.value
            if safety_assessment and isinstance(safety_assessment.classification, SafetyClassification)
            else (safety_assessment.classification if safety_assessment else "SAFE")
        )
        risk_score = safety_assessment.score if safety_assessment else 0

        # 2. Determine initial priority & routing recommendation
        route = RouteClass.NO_AI
        priority = RoutingPriority.LOW
        reason = ""
        escalated = False

        # Hard invariant baseline checks based on technical safety classification (V0.3 authoritative)
        if risk_class == SafetyClassification.CRITICAL.value:
            route = RouteClass.STRONG_AI
            priority = RoutingPriority.CRITICAL
            reason = "CRITICAL security classification requires strong reasoning."

        elif risk_class == SafetyClassification.HIGH_RISK.value:
            route = RouteClass.STRONG_AI
            priority = RoutingPriority.HIGH
            reason = "HIGH_RISK security classification requires strong reasoning."

        elif risk_class == SafetyClassification.MEDIUM_RISK.value:
            route = RouteClass.FAST_AI
            priority = RoutingPriority.MEDIUM
            reason = "MEDIUM_RISK security classification requires fast AI evaluation."

        elif risk_class == SafetyClassification.LOW_RISK.value:
            if complexity >= 40 or uncertainty >= 40 or sensitivity_score >= 50:
                route = RouteClass.FAST_AI
                priority = RoutingPriority.MEDIUM
                reason = "LOW_RISK command with elevated complexity/uncertainty requires fast AI evaluation."
            else:
                route = RouteClass.FAST_AI
                priority = RoutingPriority.LOW
                reason = "LOW_RISK routine command routed to fast AI model."

        else:  # SAFE
            if complexity < 30 and uncertainty < 30 and sensitivity_score < 30:
                route = RouteClass.NO_AI
                priority = RoutingPriority.LOW
                reason = "Safe action with low complexity and no contextual ambiguity."
            elif complexity < 50 and uncertainty < 50:
                route = RouteClass.FAST_AI
                priority = RoutingPriority.LOW
                reason = "SAFE action with moderate complexity/uncertainty routed to fast AI model."
            else:
                route = RouteClass.STRONG_AI
                priority = RoutingPriority.HIGH
                reason = "SAFE action with high contextual complexity/uncertainty escalated to strong AI."
                escalated = True

        # 3. Context-sensitive Escalation Rules
        # Rule A: Network + script execution (e.g., curl <script> | powershell)
        if ("curl" in command.lower() or "wget" in command.lower()) and (
            "|" in command or "powershell" in command.lower() or "sh" in command.lower()
        ):
            if route != RouteClass.STRONG_AI:
                route = RouteClass.STRONG_AI
                priority = RoutingPriority.HIGH
                reason = "Network script execution detected; escalated to STRONG_AI for deep context verification."
                escalated = True

        # Rule B: Credential access or remote state changes or unknown capabilities
        if (
            sensitivity_level in (SensitivityLevel.HIGH, SensitivityLevel.CRITICAL)
            or (safety_assessment and CapabilityType.UNKNOWN_CAPABILITY in safety_assessment.capabilities)
        ):
            if route != RouteClass.STRONG_AI:
                if risk_class in (SafetyClassification.HIGH_RISK.value, SafetyClassification.CRITICAL.value) or sensitivity_level == SensitivityLevel.CRITICAL:
                    route = RouteClass.STRONG_AI
                    priority = RoutingPriority.CRITICAL if sensitivity_level == SensitivityLevel.CRITICAL else RoutingPriority.HIGH
                    reason = "Sensitive action (credentials / remote state / unknown capability) requires STRONG_AI."
                    escalated = True
                elif route == RouteClass.NO_AI:
                    route = RouteClass.FAST_AI
                    priority = RoutingPriority.MEDIUM
                    reason = "Sensitive action requires AI supervisory evaluation."
                    escalated = True

        # Rule C: High uncertainty due to missing goal / phase conflict / compound command
        if uncertainty >= 60 and route in (RouteClass.NO_AI, RouteClass.FAST_AI):
            route = RouteClass.STRONG_AI
            priority = RoutingPriority.HIGH
            reason = "High contextual uncertainty requires STRONG_AI reasoning."
            escalated = True

        # 4. Resolve Provider and Model & Check Configuration Fallback
        provider, model = self._get_provider_config(route)

        # Handle missing or invalid provider configuration by falling back cleanly
        if route != RouteClass.NO_AI and (not provider or provider.strip() == "" or provider == "invalid"):
            route = RouteClass.FALLBACK_AI
            provider, model = self._get_provider_config(route)
            reason = f"Preferred provider unconfigured or invalid; falling back to {provider}/{model}."

        decision = RoutingDecision(
            route=route,
            reason=reason,
            provider=provider,
            model=model,
            estimated_priority=priority,
            complexity_score=complexity,
            uncertainty_score=uncertainty,
            sensitivity_level=sensitivity_level,
            safety_classification=risk_class,
            safety_score=risk_score,
            ai_call_avoided=(route == RouteClass.NO_AI),
        )

        self.metrics.record_decision(decision, escalated=escalated)
        return decision
