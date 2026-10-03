import pytest
from policy.models import PolicyDecision, PolicySeverity, PolicyReason, PolicyAssessment


def test_policy_reason_serialization():
    reason = PolicyReason(
        rule_id="POL-001",
        severity=PolicySeverity.CRITICAL,
        title="Critical Security Risk",
        explanation="Action is unsafe."
    )
    d = reason.to_dict()
    assert d["rule_id"] == "POL-001"
    assert d["severity"] == "CRITICAL"
    assert d["title"] == "Critical Security Risk"


def test_policy_assessment_to_dict_and_console():
    reason = PolicyReason(
        rule_id="POL-008",
        severity=PolicySeverity.HIGH,
        title="High Safety Risk",
        explanation="High risk push operation."
    )
    assessment = PolicyAssessment(
        decision=PolicyDecision.REVIEW,
        severity=PolicySeverity.HIGH,
        reasons=[reason],
        risk_score=75,
        ai_verdict="QUESTIONABLE",
        routing_decision="STRONG_AI",
        command="git push --force origin main",
        approval_request_id="req-12345"
    )

    d = assessment.to_dict()
    assert d["decision"] == "REVIEW"
    assert d["severity"] == "HIGH"
    assert len(d["reasons"]) == 1
    assert d["approval_request_id"] == "req-12345"

    console = assessment.render_console()
    assert "AEGIS POLICY ENGINE" in console
    assert "git push --force origin main" in console
    assert "REVIEW" in console
    assert "NOT IMPLEMENTED" in console
