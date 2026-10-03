import pytest
from protected.models import GatewayStatus, ProtectedContext
from protected.proxy import CommandProxy
from enforcement.models import ExecutionMode


def test_proxy_safe_command_permits_automatically():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("git status")

    assert res.gateway_status == GatewayStatus.PERMITTED
    assert res.policy_decision == "ALLOW"
    assert res.enforcement_status == "SIMULATED"
    assert res.approval_id is None
    # Verify automatic execution without human prompt
    assert res.execution_result is not None


def test_proxy_risky_command_pauses_for_approval():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("git push --force origin main")

    assert res.gateway_status == GatewayStatus.PAUSED_FOR_APPROVAL
    assert res.policy_decision == "REVIEW"
    assert res.enforcement_status == "WAITING_FOR_APPROVAL"
    assert res.approval_id is not None
    # Verify execution was NOT performed while waiting
    assert res.execution_result is None or res.execution_result.get("exit_code") == -1


def test_proxy_approved_command_permits_execution():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    # First submission pauses
    res1 = proxy.submit("git push --force origin main")
    req_id = res1.approval_id
    assert req_id is not None

    # Human approves request
    proxy.approval_manager.approve(req_id)

    # Resubmission after approval clears for execution
    res2 = proxy.submit("git push --force origin main")
    assert res2.gateway_status == GatewayStatus.PERMITTED
    assert res2.approval_status == "APPROVED"


def test_proxy_denied_command_rejects_execution():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res1 = proxy.submit("sudo rm /tmp/log")
    req_id = res1.approval_id
    assert req_id is not None

    # Human denies request
    proxy.approval_manager.deny(req_id)

    res2 = proxy.submit("sudo rm /tmp/log")
    assert res2.gateway_status == GatewayStatus.REJECTED_POLICY
    assert res2.approval_status == "DENIED"


def test_proxy_critical_command_blocks():
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("rm -rf /")

    assert res.gateway_status in (GatewayStatus.REJECTED_POLICY, GatewayStatus.REJECTED_SCOPE)
    assert res.policy_decision == "BLOCK"
    assert res.enforcement_status == "BLOCKED"
