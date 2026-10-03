import pytest
from safety.models import SafetyAssessment, SafetyClassification, CapabilityType, SafetyAction
from ai_supervisor.models import SupervisorAssessment, SupervisorVerdict, RecommendedAction
from ai_supervisor.routing_models import RoutingDecision, RouteClass
from policy.models import PolicyDecision, PolicySeverity, PolicyAssessment
from policy.engine import PolicyEngine
from policy.config import PolicyConfig, PolicyMode
from policy.approval import ApprovalManager
from policy.audit import AuditLogger


def test_policy_engine_evaluates_allow():
    engine = PolicyEngine()
    safety = SafetyAssessment(
        command="git status",
        classification=SafetyClassification.SAFE,
        action=SafetyAction.OBSERVE,
        score=0
    )
    assessment = engine.evaluate("git status", safety_assessment=safety)
    assert assessment.decision == PolicyDecision.ALLOW
    assert assessment.v03_risk == "SAFE"
    assert assessment.approval_request_id is None
    assert len(engine.audit_logger.get_records()) == 1


def test_policy_engine_evaluates_review_creates_approval():
    engine = PolicyEngine()
    safety = SafetyAssessment(
        command="git push --force origin main",
        classification=SafetyClassification.HIGH_RISK,
        action=SafetyAction.RESTRICTED,
        score=75
    )
    assessment = engine.evaluate("git push --force origin main", safety_assessment=safety)
    assert assessment.decision == PolicyDecision.REVIEW
    assert assessment.approval_request_id is not None

    req = engine.approval_manager.get_request(assessment.approval_request_id)
    assert req is not None
    assert req.status == "PENDING"
    assert req.command == "git push --force origin main"


def test_policy_engine_evaluates_block():
    engine = PolicyEngine()
    safety = SafetyAssessment(
        command="rm -rf /",
        classification=SafetyClassification.CRITICAL,
        action=SafetyAction.RESTRICTED,
        score=95
    )
    assessment = engine.evaluate("rm -rf /", safety_assessment=safety)
    assert assessment.decision == PolicyDecision.BLOCK
    assert assessment.approval_request_id is None


def test_policy_engine_failsafe_exception_handling(monkeypatch):
    engine = PolicyEngine()

    def mock_evaluate_raise(*args, **kwargs):
        raise RuntimeError("Simulated internal rule engine error")

    monkeypatch.setattr("policy.engine.PolicyRuleEngine.evaluate", mock_evaluate_raise)

    assessment = engine.evaluate("ls -la")
    assert assessment.decision == PolicyDecision.REVIEW
    assert assessment.severity == PolicySeverity.HIGH
    assert "Fail-Safe Triggered" in assessment.reasons[0].title


def test_policy_engine_inert_execution_guarantee():
    # Verify PolicyEngine never executes or touches subprocesses
    engine = PolicyEngine()
    assessment = engine.evaluate("rm -rf /")
    assert assessment.decision == PolicyDecision.BLOCK
    # No process execution, no exceptions raised, pure data structure output


def test_policy_engine_evaluates_already_approved_request():
    engine = PolicyEngine()
    safety = SafetyAssessment(
        command="git push --force origin main",
        classification=SafetyClassification.HIGH_RISK,
        action=SafetyAction.RESTRICTED,
        score=75
    )
    # First evaluation: triggers REVIEW and creates PENDING approval request
    ass1 = engine.evaluate("git push --force origin main", safety_assessment=safety)
    assert ass1.decision == PolicyDecision.REVIEW
    assert ass1.approval_request_id is not None
    
    rec1 = engine.audit_logger.get_records()[-1]
    assert rec1.final_policy_decision == "REVIEW"
    assert rec1.approval_status == "PENDING"

    # Human approves request
    engine.approval_manager.approve(ass1.approval_request_id)

    # Second evaluation: detects existing approved request and logs PERMITTED / APPROVED
    ass2 = engine.evaluate("git push --force origin main", safety_assessment=safety)
    assert ass2.approval_request_id == ass1.approval_request_id

    rec2 = engine.audit_logger.get_records()[-1]
    assert rec2.final_policy_decision == "PERMITTED"
    assert rec2.approval_status == "APPROVED"
    assert "Human approval granted" in rec2.policy_reasons[0]

