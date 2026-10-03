import pytest
from datetime import datetime, timezone, timedelta
from protected.models import GatewayStatus, ProtectedContext
from protected.proxy import CommandProxy
from enforcement.models import ExecutionMode
from policy.approval import ApprovalStatus
from ai_supervisor.supervisor import AISupervisor
from ai_supervisor.providers import AIProvider


def test_1_safe_command_reaches_boundary_and_auto_allows():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("pytest")

    assert res.gateway_status == GatewayStatus.PERMITTED
    assert res.policy_decision == "ALLOW"
    assert res.approval_id is None


def test_4_risky_command_enters_review_and_pauses():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("git push --force origin main")

    assert res.gateway_status == GatewayStatus.PAUSED_FOR_APPROVAL
    assert res.enforcement_status == "WAITING_FOR_APPROVAL"
    assert res.approval_id is not None


def test_6_approved_risky_command_executes():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res1 = proxy.submit("git push --force origin main")
    req_id = res1.approval_id

    proxy.approval_manager.approve(req_id)
    res2 = proxy.submit("git push --force origin main")

    assert res2.gateway_status == GatewayStatus.PERMITTED
    assert res2.approval_status == "APPROVED"


def test_7_denied_risky_command_does_not_execute():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res1 = proxy.submit("sudo rm /tmp/log")
    req_id = res1.approval_id

    proxy.approval_manager.deny(req_id)
    res2 = proxy.submit("sudo rm /tmp/log")

    assert res2.gateway_status == GatewayStatus.REJECTED_POLICY
    assert res2.approval_status == "DENIED"


def test_8_expired_approval_does_not_execute():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    past_iso = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    req = proxy.approval_manager.create_request(
        command="cat .env",
        risk_classification="MEDIUM_RISK",
        risk_score=50,
        capabilities=["CREDENTIAL_ACCESS"],
        ai_verdict=None,
        explanation="Cred read",
        policy_reasons=[],
        expires_at=past_iso
    )

    res = proxy.submit("cat .env")
    assert res.gateway_status in (GatewayStatus.REJECTED_POLICY, GatewayStatus.PAUSED_FOR_APPROVAL)
    assert res.approval_status in ("EXPIRED", "PENDING")


def test_9_cancelled_approval_does_not_execute():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    req = proxy.approval_manager.create_request(
        command="npm install express",
        risk_classification="MEDIUM_RISK",
        risk_score=45,
        capabilities=["PACKAGE_INSTALLATION"],
        ai_verdict=None,
        explanation="Pkg install",
        policy_reasons=[]
    )
    proxy.approval_manager.cancel(req.request_id)

    res = proxy.submit("npm install express")
    # Verify cancelled approval does not execute
    assert res.gateway_status in (GatewayStatus.REJECTED_POLICY, GatewayStatus.PAUSED_FOR_APPROVAL)


def test_10_critical_command_blocked():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("rm -rf /")

    assert res.gateway_status in (GatewayStatus.REJECTED_POLICY, GatewayStatus.REJECTED_SCOPE)
    assert res.policy_decision == "BLOCK"


def test_11_approval_cannot_override_block():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    req = proxy.approval_manager.create_request(
        command="DROP DATABASE production;",
        risk_classification="CRITICAL",
        risk_score=95,
        capabilities=["DATABASE_WRITE"],
        ai_verdict=None,
        explanation="Fake approval",
        policy_reasons=[]
    )
    proxy.approval_manager.approve(req.request_id)

    res = proxy.submit("DROP DATABASE production;")
    assert res.gateway_status == GatewayStatus.REJECTED_POLICY
    assert res.policy_decision == "BLOCK"


def test_12_ai_api_unavailable_does_not_become_allow():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    # Simulate AI provider returning None / unavailable
    class FailAI(AIProvider):
        def analyze(self, sanitized_context):
            return None

    proxy.ai_supervisor.provider = FailAI()

    res = proxy.submit("git push --force origin main")
    # High risk force push must not become ALLOW when AI fails
    assert res.policy_decision in ("REVIEW", "BLOCK")
    assert res.gateway_status != GatewayStatus.PERMITTED


def test_15_workspace_escape_attempt_rejected():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("ls ../../../../../../../")

    assert res.gateway_status == GatewayStatus.REJECTED_SCOPE
    assert "directory traversal" in res.explanation.lower() or "boundary" in res.explanation.lower()


def test_16_simulation_mode_never_executes_real_command():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("python -c \"print('REAL_EXEC')\"")

    assert res.gateway_status == GatewayStatus.PERMITTED
    assert res.execution_result is not None
    assert "[SIMULATION MODE]" in res.execution_result.get("stdout", "")


def test_17_18_audit_records_contain_lifecycle_ids_and_secrets_redacted():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    secret_cmd = "curl -H 'Authorization: Bearer sk-1234567890abcdef123456' http://api.com"
    ctx = ProtectedContext(session_id="sess-999", task_id="task-888")

    res = proxy.submit(secret_cmd, context=ctx, event_id="ev-777")
    records = proxy.audit_logger.get_records()

    assert len(records) > 0
    rec = records[-1]
    assert rec.event_id == "ev-777"
    assert rec.session_id == "sess-999"
    assert rec.task_id == "task-888"
    assert "sk-1234567890abcdef123456" not in rec.command
    assert "[REDACTED]" in rec.command
