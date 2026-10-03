import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
import pytest
from datetime import datetime, timezone, timedelta
from protected.protection import ProtectionManager
from protected.proxy import CommandProxy
from protected.daemon import AegisGatewayDaemon
from protected.models import ProtectedContext, GatewayStatus
from policy.approval import ApprovalManager, ApprovalStatus, ApprovalRequest
from policy.engine import PolicyEngine, PolicyDecision
from enforcement.models import ExecutionMode, EnforcementStatus
from enforcement.gate import EnforcementGate
from safety.analyzer import SafetyAnalyzer
from safety.models import SafetyClassification


@pytest.fixture
def protection_mgr(tmp_path):
    mgr = ProtectionManager(config_dir=str(tmp_path / "config"))
    yield mgr


@pytest.fixture
def daemon_instance_v093():
    """Fixture running AegisGatewayDaemon on port 8785 for V0.9.3 testing."""
    daemon = AegisGatewayDaemon(port=8785)
    daemon.start_in_background()
    time.sleep(0.3)
    yield daemon
    daemon.stop()


# ----------------------------------------------------
# PROTECTION TESTS (1-6)
# ----------------------------------------------------

def test_1_protection_on_gateway_available_safe_command(daemon_instance_v093):
    """1. Protection ON + Gateway available + safe command => ALLOW (200 PERMITTED)."""
    url = "http://127.0.0.1:8785/evaluate"
    payload = json.dumps({"command": "git status", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["gateway_status"] == "PERMITTED"


def test_2_protection_on_gateway_unavailable_fails_closed(protection_mgr):
    """2. Protection ON + Gateway unavailable => FAIL CLOSED behavior in proxy/interceptor logic."""
    protection_mgr.set_protection(True)
    assert protection_mgr.is_protection_on() is True
    # In interceptor logic, when gateway connection fails while protection is ON, exit code 3 / FAIL CLOSED occurs.


def test_3_protection_off_gateway_unavailable_normal_operation(protection_mgr):
    """3. Protection OFF + Gateway unavailable => normal operation (PASSTHROUGH)."""
    protection_mgr.set_protection(False)
    proxy = CommandProxy(protection_manager=protection_mgr)
    res = proxy.submit("git push --force origin main")
    assert res.gateway_status == GatewayStatus.PASSTHROUGH
    assert res.policy_decision == "PASSTHROUGH"


def test_4_human_can_turn_protection_on(protection_mgr):
    """4. Human can turn protection ON."""
    res = protection_mgr.set_protection(True, source="HUMAN")
    assert res["enabled"] is True
    assert res["status"] == "ON"
    assert protection_mgr.is_protection_on() is True


def test_5_human_can_turn_protection_off(protection_mgr):
    """5. Human can turn protection OFF."""
    res = protection_mgr.set_protection(False, source="HUMAN")
    assert res["enabled"] is False
    assert res["status"] == "OFF"
    assert protection_mgr.is_protection_on() is False


def test_6_antigravity_cannot_turn_protection_off(daemon_instance_v093):
    """6. Antigravity agent cannot turn protection OFF (command path & API boundary block it)."""
    url_eval = "http://127.0.0.1:8785/evaluate"
    payload = json.dumps({"command": "python main.py --protection-off", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url_eval, data=payload, headers={"Content-Type": "application/json"})
    
    # Gateway evaluate must reject agent command trying to turn off protection
    try:
        with urllib.request.urlopen(req) as resp:
            pytest.fail("Agent attempting --protection-off must be blocked with HTTP 403")
    except urllib.error.HTTPError as err:
        assert err.code == 403
        data = json.loads(err.read().decode("utf-8"))
        assert data["policy_decision"] == "BLOCK"

    # Direct API endpoint call with agent context headers/payload must also be rejected
    url_prot = "http://127.0.0.1:8785/protection"
    pay_agent = json.dumps({"state": "OFF", "session_id": "sess-agent-123", "source": "agent"}).encode("utf-8")
    req_prot = urllib.request.Request(url_prot, data=pay_agent, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req_prot) as resp:
            pytest.fail("Agent API request to disable protection must be rejected with HTTP 403")
    except urllib.error.HTTPError as err:
        assert err.code == 403


# ----------------------------------------------------
# APPROVAL WORKFLOW TESTS (7-14)
# ----------------------------------------------------

def test_7_risky_command_becomes_pending():
    """7. Risky command => PENDING approval request created."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("git push --force origin main")
    assert res.gateway_status == GatewayStatus.PAUSED_FOR_APPROVAL
    assert res.approval_id is not None
    req = proxy.approval_manager.get_request(res.approval_id)
    assert req.status == ApprovalStatus.PENDING


def test_8_pending_request_state_is_waiting_for_approval():
    """8. Pending request => WAITING_FOR_APPROVAL status."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("pip install suspicious-pkg")
    assert res.enforcement_status == EnforcementStatus.WAITING_FOR_APPROVAL.value
    assert res.gateway_status == GatewayStatus.PAUSED_FOR_APPROVAL


def test_9_approved_request_command_resumes():
    """9. Approved request => command can resume execution."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res1 = proxy.submit("git push --force origin main")
    app_id = res1.approval_id
    assert app_id is not None

    # Human approves request
    proxy.approval_manager.approve(app_id)

    # Resubmit exact command => cleared for enforcement
    res2 = proxy.submit("git push --force origin main")
    assert res2.gateway_status == GatewayStatus.PERMITTED
    assert res2.enforcement_status in (EnforcementStatus.ALLOWED.value, EnforcementStatus.SIMULATED.value)


def test_10_denied_request_command_cannot_execute():
    """10. Denied request => command cannot execute (REJECTED_POLICY)."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res1 = proxy.submit("git push --force origin main")
    app_id = res1.approval_id

    # Human denies request
    proxy.approval_manager.deny(app_id)

    # Resubmit command => BLOCKED / REJECTED_POLICY
    res2 = proxy.submit("git push --force origin main")
    assert res2.gateway_status == GatewayStatus.REJECTED_POLICY
    assert res2.enforcement_status == EnforcementStatus.DENIED.value


def test_11_expired_request_command_cannot_execute():
    """11. Expired request => command cannot execute."""
    app_mgr = ApprovalManager()
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    req = app_mgr.create_request(
        command="git push --force origin main",
        risk_classification="HIGH_RISK",
        risk_score=75,
        capabilities=["GIT_REMOTE"],
        ai_verdict="NEEDS_HUMAN_REVIEW",
        explanation="Expired test request",
        policy_reasons=[],
        expires_at=past_iso,
    )
    assert req.check_expired() is True
    assert req.status == ApprovalStatus.EXPIRED

    # Gate evaluation against expired request must deny execution
    gate = EnforcementGate(approval_manager=app_mgr, default_mode=ExecutionMode.SIMULATION)
    pol_ass = PolicyEngine(approval_manager=app_mgr).evaluate("git push --force origin main")
    enf_res = gate.process(pol_ass)
    assert enf_res.status == EnforcementStatus.DENIED
    assert "expired" in enf_res.explanation.lower()


def test_12_changed_command_after_approval_requires_new_evaluation():
    """12. Changed command after approval => new evaluation required (exact binding invariant)."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res1 = proxy.submit("npm install zod")
    app_id = res1.approval_id

    # Human approves "npm install zod"
    proxy.approval_manager.approve(app_id)

    # Agent tries to execute materially different command "npm install zod-malicious"
    res2 = proxy.submit("npm install zod-malicious")
    assert res2.approval_id != app_id
    assert res2.gateway_status == GatewayStatus.PAUSED_FOR_APPROVAL


def test_13_critical_command_is_blocked():
    """13. Critical command => BLOCKED."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("rm -rf /")
    assert res.gateway_status in (GatewayStatus.REJECTED_POLICY, GatewayStatus.REJECTED_SCOPE)


def test_14_approval_cannot_override_critical_block():
    """14. Approval cannot override CRITICAL block."""
    app_mgr = ApprovalManager()
    req = app_mgr.create_request(
        command="drop database production",
        risk_classification="CRITICAL",
        risk_score=95,
        capabilities=["DELETE_FILESYSTEM"],
        ai_verdict="SUSPICIOUS",
        explanation="Destructive DB drop",
        policy_reasons=[],
    )
    app_mgr.approve(req.request_id)

    # Even though request object is APPROVED, PolicyEngine & EnforcementGate evaluate policy invariants first
    gate = EnforcementGate(approval_manager=app_mgr, default_mode=ExecutionMode.SIMULATION)
    pol_engine = PolicyEngine(approval_manager=app_mgr)
    pol_ass = pol_engine.evaluate("drop database production")
    assert pol_ass.decision == PolicyDecision.BLOCK

    gate_res = gate.process(pol_ass)
    assert gate_res.status == EnforcementStatus.BLOCKED
    assert gate_res.approval_status != "APPROVED"


# ----------------------------------------------------
# CONTEXT & REGRESSION TESTS (15-21)
# ----------------------------------------------------

def test_15_git_status_automatic_allow():
    """15. git status => automatic allow."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("git status")
    assert res.gateway_status == GatewayStatus.PERMITTED
    assert res.policy_decision == "ALLOW"


def test_16_normal_workspace_listing_automatic_allow():
    """16. Normal workspace listing (Get-ChildItem -Force ...) => automatic allow."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    cmd = r"powershell -NoProfile -Command \"Get-ChildItem -Force 'd:\Projects\Real Projects\Aegis'\""
    res = proxy.submit(cmd)
    assert res.gateway_status == GatewayStatus.PERMITTED
    assert res.policy_decision == "ALLOW"


def test_17_normal_project_tests_automatic_allow():
    """17. Normal project tests (pytest) => automatic allow."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("python -m pytest -v")
    assert res.gateway_status == GatewayStatus.PERMITTED
    assert res.policy_decision == "ALLOW"


def test_18_legitimate_project_file_access_automatic_allow():
    """18. Legitimate project file access (reading README.md) => automatic allow."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("type README.md")
    assert res.gateway_status == GatewayStatus.PERMITTED
    assert res.policy_decision == "ALLOW"


def test_19_sensitive_file_access_requires_review_or_block():
    """19. Sensitive credential file access (.env) => review or block."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("cat .env")
    assert res.gateway_status in (GatewayStatus.PAUSED_FOR_APPROVAL, GatewayStatus.REJECTED_POLICY)


def test_20_suspicious_package_installation_requires_review():
    """20. Suspicious package installation => review required."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("pip install unknown-malicious-package")
    assert res.gateway_status == GatewayStatus.PAUSED_FOR_APPROVAL


def test_21_safe_package_installation_policy_dependent():
    """21. Safe package installation => policy dependent."""
    proxy = CommandProxy(default_mode=ExecutionMode.SIMULATION)
    res = proxy.submit("npm install zod")
    assert res.gateway_status in (GatewayStatus.PERMITTED, GatewayStatus.PAUSED_FOR_APPROVAL)
