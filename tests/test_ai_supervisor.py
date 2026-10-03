import pytest
from ai_supervisor.supervisor import AISupervisor
from ai_supervisor.providers import MockProvider, OpenAIProvider
from ai_supervisor.models import SupervisorVerdict, SupervisorAlignment, RecommendedAction
from supervisor.state import SessionState
from safety.models import SafetyAssessment, SafetyClassification, SafetyAction, CapabilityType, Reversibility, Scope


def test_ai_supervisor_mock_aligned():
    supervisor = AISupervisor(provider=MockProvider())
    state = SessionState(session_id="s1", started_at="T1", last_activity="T2", current_goal="Fix parser tests", current_phase="VERIFICATION")

    safety = SafetyAssessment(
        command="python -m pytest -v",
        classification=SafetyClassification.SAFE,
        action=SafetyAction.OBSERVE,
        score=0,
        capabilities=[CapabilityType.EXECUTE_PROCESS],
        reversibility=Reversibility.REVERSIBLE,
        scope=Scope.INSIDE_PROJECT
    )

    assessment = supervisor.analyze("python -m pytest -v", session_state=state, safety_assessment=safety)

    assert assessment.verdict == SupervisorVerdict.ALIGNED
    assert assessment.alignment == SupervisorAlignment.ALIGNED
    assert assessment.recommended_action == RecommendedAction.NO_CONCERN
    assert "aligns" in assessment.explanation.lower()


def test_ai_supervisor_mock_questionable_package_install():
    supervisor = AISupervisor(provider=MockProvider())
    state = SessionState(session_id="s1", started_at="T1", last_activity="T2", current_goal="Fix parser tests", current_phase="DEBUGGING")

    safety = SafetyAssessment(
        command="pip install requests",
        classification=SafetyClassification.MEDIUM_RISK,
        action=SafetyAction.REVIEW_REQUIRED,
        score=30,
        capabilities=[CapabilityType.PACKAGE_INSTALLATION, CapabilityType.NETWORK_ACCESS],
        reversibility=Reversibility.PARTIALLY_REVERSIBLE,
        scope=Scope.INSIDE_PROJECT
    )

    assessment = supervisor.analyze("pip install requests", session_state=state, safety_assessment=safety)

    assert assessment.verdict == SupervisorVerdict.QUESTIONABLE
    assert assessment.recommended_action == RecommendedAction.REVIEW
    assert len(assessment.concerns) > 0


def test_ai_supervisor_mock_suspicious_force_push():
    supervisor = AISupervisor(provider=MockProvider())
    state = SessionState(session_id="s1", started_at="T1", last_activity="T2", current_goal="Fix parser tests", current_phase="DEBUGGING")

    safety = SafetyAssessment(
        command="git push --force origin main",
        classification=SafetyClassification.HIGH_RISK,
        action=SafetyAction.REVIEW_REQUIRED,
        score=55,
        capabilities=[CapabilityType.REMOTE_STATE_CHANGE, CapabilityType.GIT_REMOTE],
        reversibility=Reversibility.DIFFICULT_TO_REVERSE,
        scope=Scope.INSIDE_PROJECT
    )

    assessment = supervisor.analyze("git push --force origin main", session_state=state, safety_assessment=safety)

    assert assessment.verdict in [SupervisorVerdict.NEEDS_HUMAN_REVIEW, SupervisorVerdict.SUSPICIOUS]
    assert assessment.alignment != SupervisorAlignment.ALIGNED


def test_ai_supervisor_v03_override_prevention():
    """Ensure AI cannot downgrade deterministic HIGH_RISK / CRITICAL V0.3 findings to ALIGNED."""
    class FakeLyingProvider:
        def analyze(self, ctx):
            # Lying provider claims dangerous action is ALIGNED!
            return {
                "verdict": "ALIGNED",
                "confidence": "HIGH",
                "alignment": "ALIGNED",
                "explanation": "This looks fine.",
                "concerns": [],
                "recommended_action": "NO_CONCERN"
            }

    supervisor = AISupervisor(provider=FakeLyingProvider())
    safety_critical = SafetyAssessment(
        command="rm -rf /",
        classification=SafetyClassification.CRITICAL,
        action=SafetyAction.RESTRICTED,
        score=80,
        capabilities=[CapabilityType.DELETE_FILESYSTEM],
        reversibility=Reversibility.IRREVERSIBLE,
        scope=Scope.OUTSIDE_PROJECT
    )

    assessment = supervisor.analyze("rm -rf /", safety_assessment=safety_critical)

    # Must NOT be ALIGNED because V0.3 was CRITICAL!
    assert assessment.verdict != SupervisorVerdict.ALIGNED
    assert assessment.verdict == SupervisorVerdict.NEEDS_HUMAN_REVIEW
    assert any("cannot override" in c for c in assessment.concerns)


def test_ai_supervisor_unavailable_graceful_fallback():
    # OpenAIProvider without API key
    provider = OpenAIProvider(api_key=None)
    supervisor = AISupervisor(provider=provider)

    assessment = supervisor.analyze("python main.py")

    assert assessment.verdict == SupervisorVerdict.UNAVAILABLE
    assert "unavailable" in assessment.explanation.lower()
