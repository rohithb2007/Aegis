import pytest
from datetime import datetime, timezone, timedelta
from safety.models import SafetyAssessment, SafetyClassification, CapabilityType
from policy.models import PolicyAssessment, PolicyDecision, PolicySeverity, PolicyReason
from policy.approval import ApprovalManager, ApprovalStatus
from enforcement.models import EnforcementStatus, ExecutionMode
from enforcement.gate import EnforcementGate


def test_gate_allow_policy_auto_permits():
    mgr = ApprovalManager()
    gate = EnforcementGate(approval_manager=mgr, default_mode=ExecutionMode.CONTROLLED)

    policy_ass = PolicyAssessment(
        decision=PolicyDecision.ALLOW,
        severity=PolicySeverity.INFORMATIONAL,
        reasons=[PolicyReason("POL-014", PolicySeverity.INFORMATIONAL, "Safe", "Routine safe action")],
        command="git status",
        v03_risk="SAFE"
    )

    result = gate.process(policy_ass)
    assert result.status == EnforcementStatus.ALLOWED
    assert result.approval_status == "AUTO_ALLOWED"
    assert "automatically" in result.explanation.lower()


def test_gate_review_without_approval_waits():
    mgr = ApprovalManager()
    gate = EnforcementGate(approval_manager=mgr, default_mode=ExecutionMode.CONTROLLED)

    policy_ass = PolicyAssessment(
        decision=PolicyDecision.REVIEW,
        severity=PolicySeverity.HIGH,
        reasons=[PolicyReason("POL-009", PolicySeverity.HIGH, "Force Push", "Force push requires review")],
        command="git push --force origin main",
        v03_risk="HIGH_RISK"
    )

    result = gate.process(policy_ass)
    assert result.status == EnforcementStatus.WAITING_FOR_APPROVAL
    assert result.approval_id is not None
    assert result.approval_status == "PENDING"


def test_gate_review_with_approval_grants_access():
    mgr = ApprovalManager()
    gate = EnforcementGate(approval_manager=mgr, default_mode=ExecutionMode.CONTROLLED)

    req = mgr.create_request(
        command="git push --force origin main",
        risk_classification="HIGH_RISK",
        risk_score=75,
        capabilities=["REMOTE_STATE_CHANGE"],
        ai_verdict="QUESTIONABLE",
        explanation="Force push",
        policy_reasons=[]
    )
    mgr.approve(req.request_id)

    policy_ass = PolicyAssessment(
        decision=PolicyDecision.REVIEW,
        severity=PolicySeverity.HIGH,
        reasons=[PolicyReason("POL-009", PolicySeverity.HIGH, "Force Push", "Force push")],
        command="git push --force origin main",
        approval_request_id=req.request_id,
        v03_risk="HIGH_RISK"
    )

    result = gate.process(policy_ass)
    assert result.status == EnforcementStatus.ALLOWED
    assert result.approval_status == "APPROVED"


def test_gate_review_denied_denies_enforcement():
    mgr = ApprovalManager()
    gate = EnforcementGate(approval_manager=mgr)

    req = mgr.create_request(
        command="sudo rm /tmp/log",
        risk_classification="HIGH_RISK",
        risk_score=80,
        capabilities=["PRIVILEGE_ESCALATION"],
        ai_verdict="SUSPICIOUS",
        explanation="Sudo execution",
        policy_reasons=[]
    )
    mgr.deny(req.request_id)

    policy_ass = PolicyAssessment(
        decision=PolicyDecision.REVIEW,
        severity=PolicySeverity.HIGH,
        reasons=[PolicyReason("POL-006", PolicySeverity.HIGH, "Sudo", "Sudo")],
        command="sudo rm /tmp/log",
        approval_request_id=req.request_id,
        v03_risk="HIGH_RISK"
    )

    result = gate.process(policy_ass)
    assert result.status == EnforcementStatus.DENIED
    assert result.approval_status == "DENIED"


def test_gate_review_expired_denies_enforcement():
    mgr = ApprovalManager()
    gate = EnforcementGate(approval_manager=mgr)

    past_iso = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    req = mgr.create_request(
        command="cat .env",
        risk_classification="MEDIUM_RISK",
        risk_score=50,
        capabilities=["CREDENTIAL_ACCESS"],
        ai_verdict=None,
        explanation="Credential read",
        policy_reasons=[],
        expires_at=past_iso
    )

    policy_ass = PolicyAssessment(
        decision=PolicyDecision.REVIEW,
        severity=PolicySeverity.MEDIUM,
        reasons=[PolicyReason("POL-005C", PolicySeverity.MEDIUM, "Cred Read", "Cred Read")],
        command="cat .env",
        approval_request_id=req.request_id,
        v03_risk="MEDIUM_RISK"
    )

    result = gate.process(policy_ass)
    assert result.status == EnforcementStatus.DENIED
    assert result.approval_status == "EXPIRED"


def test_gate_block_always_blocks():
    mgr = ApprovalManager()
    gate = EnforcementGate(approval_manager=mgr)

    policy_ass = PolicyAssessment(
        decision=PolicyDecision.BLOCK,
        severity=PolicySeverity.CRITICAL,
        reasons=[PolicyReason("POL-001", PolicySeverity.CRITICAL, "Critical Risk", "Root delete")],
        command="rm -rf /",
        v03_risk="CRITICAL"
    )

    result = gate.process(policy_ass)
    assert result.status == EnforcementStatus.BLOCKED
    assert result.approval_status == "NOT_AVAILABLE"


def test_gate_failsafe_exception_handling(monkeypatch):
    gate = EnforcementGate()

    def mock_raise(*args, **kwargs):
        raise RuntimeError("Gate error")

    monkeypatch.setattr(gate, "_evaluate_gate", mock_raise)

    policy_ass = PolicyAssessment(
        decision=PolicyDecision.ALLOW,
        severity=PolicySeverity.INFORMATIONAL,
        command="git status"
    )

    res = gate.process(policy_ass)
    assert res.status == EnforcementStatus.FAILED
    assert "fail-safe" in res.explanation.lower()
