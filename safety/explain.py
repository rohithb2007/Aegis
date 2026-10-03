from .models import SafetyAssessment, CapabilityType


class SafetyExplainer:
    """Renders SafetyAssessment objects into clean ASCII human-readable security reports."""

    @staticmethod
    def render_console(assessment: SafetyAssessment) -> str:
        """Render formatted ASCII security report box."""
        caps_str = "\n  - ".join([c.value if isinstance(c, CapabilityType) else str(c) for c in assessment.capabilities]) if assessment.capabilities else "None"
        reasons_str = "\n  - ".join(assessment.reasons) if assessment.reasons else "None"

        lines = [
            "+====================================+",
            "|        AEGIS SAFETY ANALYSIS       |",
            "+====================================+",
            f"Command:",
            f"  {assessment.command}",
            "",
            f"Classification:",
            f"  {assessment.classification.value if hasattr(assessment.classification, 'value') else assessment.classification}",
            "",
            f"Score:",
            f"  {assessment.score}",
            "",
            "Capabilities:",
            f"  - {caps_str}",
            "",
            f"Scope:",
            f"  {assessment.scope.value if hasattr(assessment.scope, 'value') else assessment.scope}",
            "",
            f"Reversibility:",
            f"  {assessment.reversibility.value if hasattr(assessment.reversibility, 'value') else assessment.reversibility}",
            "",
            f"Confidence:",
            f"  {assessment.confidence}",
            "",
            "Reasons:",
            f"  - {reasons_str}",
            "",
            f"Action Label:",
            f"  {assessment.action.value if hasattr(assessment.action, 'value') else assessment.action}",
            "",
            f"Enforcement:",
            f"  OBSERVE_ONLY (V0.3 Analysis Only)",
            "+====================================+"
        ]
        return "\n".join(lines)
