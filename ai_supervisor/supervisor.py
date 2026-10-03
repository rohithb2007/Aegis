import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from .models import (
    SupervisorVerdict, SupervisorAlignment, RecommendedAction, SupervisorAssessment
)
from .sanitizer import ContextSanitizer
from .providers import AIProvider, get_provider_from_env, MockProvider
from supervisor.state import SessionState
from safety.models import SafetyAssessment, SafetyClassification


class AISupervisor:
    """Contextual AI Security Supervisor coordinator (Advisory Only)."""

    def __init__(self, provider: Optional[AIProvider] = None):
        self.sanitizer = ContextSanitizer()
        self.provider = provider or get_provider_from_env()

    def analyze(
        self,
        command: str,
        session_state: Optional[SessionState] = None,
        safety_assessment: Optional[SafetyAssessment] = None
    ) -> SupervisorAssessment:
        """Perform contextual security analysis (Advisory information only; zero command execution)."""
        timestamp = datetime.now(timezone.utc).isoformat()
        cmd_clean = command or (safety_assessment.command if safety_assessment else "")

        # 1. Build sanitized context
        sanitized_ctx = self.sanitizer.sanitize_context(
            session_state=session_state,
            safety_assessment=safety_assessment,
            current_command=cmd_clean
        )

        # 2. Invoke Provider
        raw_res = None
        try:
            raw_res = self.provider.analyze(sanitized_ctx)
        except Exception:
            raw_res = None

        if not raw_res:
            # Fallback if provider unavailable or credentials missing
            return SupervisorAssessment(
                verdict=SupervisorVerdict.UNAVAILABLE,
                confidence="HIGH",
                alignment=SupervisorAlignment.UNKNOWN,
                explanation="AI Supervisor unavailable: No provider credentials configured or network offline.",
                concerns=["Provider unavailable"],
                recommended_action=RecommendedAction.UNKNOWN,
                model=getattr(self.provider, "model", "mock-supervisor"),
                timestamp=timestamp,
                session_id=session_state.session_id if session_state else None,
                task_id=session_state.active_task_id if session_state else None,
                command=cmd_clean,
                safety_classification=safety_assessment.classification.value if safety_assessment and hasattr(safety_assessment.classification, 'value') else None,
                safety_score=safety_assessment.score if safety_assessment else None
            )

        # 3. Parse & Validate Fields
        try:
            verdict_str = str(raw_res.get("verdict", "UNKNOWN")).upper()
            verdict = SupervisorVerdict(verdict_str) if verdict_str in SupervisorVerdict.__members__ else SupervisorVerdict.UNKNOWN
        except Exception:
            verdict = SupervisorVerdict.UNKNOWN

        try:
            align_str = str(raw_res.get("alignment", "UNKNOWN")).upper()
            alignment = SupervisorAlignment(align_str) if align_str in SupervisorAlignment.__members__ else SupervisorAlignment.UNKNOWN
        except Exception:
            alignment = SupervisorAlignment.UNKNOWN

        try:
            rec_str = str(raw_res.get("recommended_action", "UNKNOWN")).upper()
            rec_action = RecommendedAction(rec_str) if rec_str in RecommendedAction.__members__ else RecommendedAction.UNKNOWN
        except Exception:
            rec_action = RecommendedAction.UNKNOWN

        confidence = str(raw_res.get("confidence", "MEDIUM")).upper()
        explanation = str(raw_res.get("explanation", "Contextual alignment evaluated."))
        concerns = raw_res.get("concerns", [])
        if not isinstance(concerns, list):
            concerns = [str(concerns)]

        # 4. Enforce V0.3 Safety Boundary: AI must NEVER downgrade deterministic V0.3 findings!
        if safety_assessment:
            classif = safety_assessment.classification.value if hasattr(safety_assessment.classification, 'value') else str(safety_assessment.classification)
            if classif in [SafetyClassification.HIGH_RISK.value, SafetyClassification.CRITICAL.value]:
                if verdict == SupervisorVerdict.ALIGNED:
                    verdict = SupervisorVerdict.NEEDS_HUMAN_REVIEW
                    alignment = SupervisorAlignment.PARTIALLY_ALIGNED
                    rec_action = RecommendedAction.REVIEW
                    concerns.append("V0.3 Safety Engine flagged action as HIGH/CRITICAL risk; AI cannot override.")

        return SupervisorAssessment(
            verdict=verdict,
            confidence=confidence,
            alignment=alignment,
            explanation=explanation,
            concerns=concerns,
            recommended_action=rec_action,
            model=getattr(self.provider, "model", "mock-supervisor"),
            timestamp=timestamp,
            session_id=session_state.session_id if session_state else None,
            task_id=session_state.active_task_id if session_state else None,
            command=cmd_clean,
            safety_classification=safety_assessment.classification.value if safety_assessment and hasattr(safety_assessment.classification, 'value') else None,
            safety_score=safety_assessment.score if safety_assessment else None
        )

    @staticmethod
    def render_console(assessment: SupervisorAssessment) -> str:
        """Render formatted ASCII AI Supervisor report box."""
        concerns_str = "\n  - ".join(assessment.concerns) if assessment.concerns else "None"

        lines = [
            "+====================================+",
            "|        AEGIS AI SUPERVISOR         |",
            "+====================================+",
            f"Command:",
            f"  {assessment.command or 'None'}",
            "",
            f"Deterministic Safety:",
            f"  {assessment.safety_classification or 'N/A'} (Score: {assessment.safety_score if assessment.safety_score is not None else 'N/A'})",
            "",
            f"AI Verdict:",
            f"  {assessment.verdict.value if hasattr(assessment.verdict, 'value') else assessment.verdict}",
            "",
            f"Confidence:",
            f"  {assessment.confidence}",
            "",
            f"Alignment:",
            f"  {assessment.alignment.value if hasattr(assessment.alignment, 'value') else assessment.alignment}",
            "",
            f"Explanation:",
            f"  {assessment.explanation}",
            "",
            "Concerns:",
            f"  - {concerns_str}",
            "",
            f"Recommended Action:",
            f"  {assessment.recommended_action.value if hasattr(assessment.recommended_action, 'value') else assessment.recommended_action}",
            "",
            f"Model:",
            f"  {assessment.model}",
            "",
            f"Enforcement:",
            f"  ADVISORY ONLY (No action executed/blocked)",
            "+====================================+"
        ]
        return "\n".join(lines)
