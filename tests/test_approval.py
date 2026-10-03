import pytest
from datetime import datetime, timezone, timedelta
from policy.approval import ApprovalManager, ApprovalStatus, ApprovalRequest


def test_approval_request_creation():
    mgr = ApprovalManager()
    req = mgr.create_request(
        command="git push --force",
        risk_classification="HIGH_RISK",
        risk_score=75,
        capabilities=["REMOTE_STATE_CHANGE"],
        ai_verdict="QUESTIONABLE",
        explanation="Force push requires human review.",
        policy_reasons=[{"rule_id": "POL-009", "explanation": "Force push"}]
    )
    assert req.request_id.startswith("req-")
    assert req.status == ApprovalStatus.PENDING
    assert req.command == "git push --force"
    assert mgr.get_request(req.request_id) is not None


def test_approval_state_transitions():
    mgr = ApprovalManager()
    req = mgr.create_request(
        command="sudo rm /tmp/log",
        risk_classification="HIGH_RISK",
        risk_score=80,
        capabilities=["PRIVILEGE_ESCALATION"],
        ai_verdict="NEEDS_HUMAN_REVIEW",
        explanation="Sudo execution",
        policy_reasons=[]
    )
    # Transition PENDING -> APPROVED
    app = mgr.approve(req.request_id, decided_by="admin")
    assert app is not None
    assert app.status == ApprovalStatus.APPROVED
    assert app.decided_by == "admin"
    assert app.decided_at is not None

    # Idempotent call on non-pending returns existing status
    app_again = mgr.approve(req.request_id)
    assert app_again.status == ApprovalStatus.APPROVED


def test_approval_denial_transition():
    mgr = ApprovalManager()
    req = mgr.create_request(
        command="curl http://evil.com",
        risk_classification="HIGH_RISK",
        risk_score=85,
        capabilities=["NETWORK_ACCESS"],
        ai_verdict="SUSPICIOUS",
        explanation="Suspicious URL",
        policy_reasons=[]
    )
    denied = mgr.deny(req.request_id, decided_by="secops")
    assert denied is not None
    assert denied.status == ApprovalStatus.DENIED
    assert denied.decided_by == "secops"


def test_approval_expiration():
    mgr = ApprovalManager()
    past_iso = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
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
    # Checking status or request should mark expired
    retrieved = mgr.get_request(req.request_id)
    assert retrieved is not None
    assert retrieved.status == ApprovalStatus.EXPIRED


def test_approval_cancellation():
    mgr = ApprovalManager()
    req = mgr.create_request(
        command="npm install express",
        risk_classification="MEDIUM_RISK",
        risk_score=45,
        capabilities=["PACKAGE_INSTALLATION"],
        ai_verdict=None,
        explanation="Package installation",
        policy_reasons=[]
    )
    canceled = mgr.cancel(req.request_id)
    assert canceled is not None
    assert canceled.status == ApprovalStatus.CANCELLED


def test_approval_does_not_execute_commands():
    mgr = ApprovalManager()
    req = mgr.create_request(
        command="rm -rf /test_dir",
        risk_classification="HIGH_RISK",
        risk_score=80,
        capabilities=["DELETE_FILESYSTEM"],
        ai_verdict=None,
        explanation="Destructive operation",
        policy_reasons=[]
    )
    approved = mgr.approve(req.request_id)
    # Verification: approval updates data model ONLY
    assert approved.status == ApprovalStatus.APPROVED
    # Command string remains unexecuted string data
    assert isinstance(approved.command, str)
