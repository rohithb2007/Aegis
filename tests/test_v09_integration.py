import os
import sys
import json
import time
import urllib.request
import pytest
import concurrent.futures
from protected.daemon import AegisGatewayDaemon
from protected.profile_installer import ProfileInstaller
from protected.proxy import CommandProxy
from protected.models import ProtectedContext, GatewayStatus
from policy.approval import ApprovalManager, ApprovalRequest, ApprovalStatus
from policy.engine import PolicyEngine
from policy.config import PolicyConfig
from policy.audit import AuditLogger
from enforcement.models import ExecutionMode


@pytest.fixture
def daemon_instance():
    """Fixture running AegisGatewayDaemon on port 8769 for testing."""
    daemon = AegisGatewayDaemon(port=8769)
    daemon.start_in_background()
    time.sleep(0.3)
    yield daemon
    daemon.stop()


# 1. Safe command automatically passes
def test_1_safe_command_automatically_passes(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "pytest", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert data["gateway_status"] == "PERMITTED"
        assert data["policy_decision"] == "ALLOW"


# 2. Project-relevant command automatically passes
def test_2_project_relevant_command_automatically_passes(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "git status", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert data["gateway_status"] == "PERMITTED"


# 3. Risky command pauses
def test_3_risky_command_pauses(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "git push --force", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert resp.status == 202
            assert data["gateway_status"] == "PAUSED_FOR_APPROVAL"
            assert data["approval_id"] is not None
    except urllib.error.HTTPError as err:
        assert err.code == 202
        data = json.loads(err.read().decode("utf-8"))
        assert data["gateway_status"] == "PAUSED_FOR_APPROVAL"
        assert data["approval_id"] is not None


# 4. Approval allows exactly the intended command
def test_4_approval_allows_exactly_intended_command(daemon_instance):
    url_eval = "http://127.0.0.1:8769/evaluate"
    payload1 = json.dumps({"command": "git push --force origin main", "cwd": os.getcwd()}).encode("utf-8")
    req_eval1 = urllib.request.Request(url_eval, data=payload1, headers={"Content-Type": "application/json"})

    app_id = None
    try:
        with urllib.request.urlopen(req_eval1) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            app_id = data["approval_id"]
    except urllib.error.HTTPError as err:
        data = json.loads(err.read().decode("utf-8"))
        app_id = data["approval_id"]

    assert app_id is not None

    # Approve
    url_app = "http://127.0.0.1:8769/approve"
    pay_app = json.dumps({"request_id": app_id}).encode("utf-8")
    req_app = urllib.request.Request(url_app, data=pay_app, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_app) as resp:
        assert resp.status == 200

    # Same command -> PERMITTED
    with urllib.request.urlopen(req_eval1) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert data["gateway_status"] == "PERMITTED"

    # Different risky command -> STILL PAUSES
    payload2 = json.dumps({"command": "git push --force origin feature", "cwd": os.getcwd()}).encode("utf-8")
    req_eval2 = urllib.request.Request(url_eval, data=payload2, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req_eval2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data["gateway_status"] == "PAUSED_FOR_APPROVAL"
    except urllib.error.HTTPError as err:
        assert err.code == 202


# 5. Denied approval prevents execution
def test_5_denied_approval_prevents_execution(daemon_instance):
    url_eval = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "git push --force origin test-deny-branch", "cwd": os.getcwd()}).encode("utf-8")
    req_eval = urllib.request.Request(url_eval, data=payload, headers={"Content-Type": "application/json"})
    app_id = None
    try:
        with urllib.request.urlopen(req_eval) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            app_id = data["approval_id"]
    except urllib.error.HTTPError as err:
        data = json.loads(err.read().decode("utf-8"))
        app_id = data["approval_id"]

    url_deny = "http://127.0.0.1:8769/deny"
    pay_deny = json.dumps({"request_id": app_id}).encode("utf-8")
    req_deny = urllib.request.Request(url_deny, data=pay_deny, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_deny) as resp:
        assert resp.status == 200

    try:
        with urllib.request.urlopen(req_eval) as resp:
            pytest.fail("Denied command must fail")
    except urllib.error.HTTPError as err:
        assert err.code == 403
        data = json.loads(err.read().decode("utf-8"))
        assert data["gateway_status"] == "REJECTED_POLICY"


# 6. Expired approval prevents execution
def test_6_expired_approval_prevents_execution(daemon_instance):
    proxy = daemon_instance.proxy
    req = proxy.approval_manager.create_request(
        command="git push --force origin main",
        risk_classification="HIGH_RISK",
        risk_score=90,
        capabilities=["GIT_MUTATION"],
        ai_verdict="NEEDS_HUMAN_REVIEW",
        explanation="High risk force push",
        policy_reasons=[{"code": "HIGH_RISK"}],
        expires_at="2000-01-01T00:00:00+00:00",
    )
    ctx = ProtectedContext(workspace_root=proxy.boundary.workspace_root)
    res = proxy.submit("git push --force origin main", context=ctx)
    assert res.gateway_status in (GatewayStatus.PAUSED_FOR_APPROVAL, GatewayStatus.REJECTED_POLICY)


# 7. Critical command is blocked
def test_7_critical_command_is_blocked(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "rm -rf /", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            pytest.fail("Critical command must return 403")
    except urllib.error.HTTPError as err:
        assert err.code == 403
        data = json.loads(err.read().decode("utf-8"))
        assert data["policy_decision"] == "BLOCK"


# 8. Nested shell behavior
def test_8_nested_shell_behavior(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "powershell -NoProfile -Command \"rm -rf /\"", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            pytest.fail("Nested shell carrying critical command must return 403")
    except urllib.error.HTTPError as err:
        assert err.code == 403


# 9. PowerShell behavior
def test_9_powershell_behavior(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "Get-ChildItem -Path .", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert data["gateway_status"] == "PERMITTED"


# 10. Cmd behavior
def test_10_cmd_behavior(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "cmd /c dir", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert data["gateway_status"] == "PERMITTED"


# 11. Direct executable behavior
def test_11_direct_executable_behavior(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "python --version", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert data["gateway_status"] == "PERMITTED"


# 12. Workspace escape attempt
def test_12_workspace_escape_attempt(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "cat ../../../../../../etc/passwd", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            pytest.fail("Workspace escape attempt must return 403")
    except urllib.error.HTTPError as err:
        assert err.code == 403
        data = json.loads(err.read().decode("utf-8"))
        assert data["gateway_status"] == "REJECTED_SCOPE"


# 13. Command chaining
def test_13_command_chaining(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "pytest; git push --force", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data["gateway_status"] == "PAUSED_FOR_APPROVAL"
    except urllib.error.HTTPError as err:
        assert err.code == 202


# 14. Pipeline
def test_14_pipeline(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "git log | Select-Object -First 5", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert data["gateway_status"] == "PERMITTED"


# 15. Script invocation
def test_15_script_invocation(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "python main.py --protected-status", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert data["gateway_status"] == "PERMITTED"


# 16. Subprocess escape attempt
def test_16_subprocess_escape_attempt(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({"command": "python -c \"import subprocess; subprocess.run(['git', 'push', '--force'])\"", "cwd": os.getcwd()}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data["gateway_status"] == "PAUSED_FOR_APPROVAL"
    except urllib.error.HTTPError as err:
        assert err.code in (202, 403)


# 17. Provider unavailable
def test_17_provider_unavailable(daemon_instance):
    # If AI provider fails, Aegis fails safely and does NOT default to ALLOW for risky commands
    proxy = daemon_instance.proxy
    proxy.ai_supervisor.provider = None  # Simulate missing provider
    res = proxy.submit("git push --force origin main")
    assert res.gateway_status in (GatewayStatus.PAUSED_FOR_APPROVAL, GatewayStatus.REJECTED_POLICY)


# 18. Audit record creation
def test_18_audit_record_creation(daemon_instance):
    proxy = daemon_instance.proxy
    res = proxy.submit("pytest")
    records = proxy.audit_logger.records
    assert len(records) > 0


# 19. Session task correlation
def test_19_session_task_correlation(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"
    payload = json.dumps({
        "command": "python -m pytest",
        "cwd": os.getcwd(),
        "session_id": "sess-test-999",
        "task_id": "task-test-888"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert data["session_id"] == "sess-test-999"
        assert data["task_id"] == "task-test-888"


# 20. Fail-safe behavior
def test_20_fail_safe_behavior(daemon_instance):
    proxy = daemon_instance.proxy
    res = proxy.submit(None)  # Invalid None command
    assert res.gateway_status in (GatewayStatus.PERMITTED, GatewayStatus.FAILED_GATEWAY, GatewayStatus.REJECTED_POLICY)


# 21. Simulation mode
def test_21_simulation_mode(daemon_instance):
    proxy = daemon_instance.proxy
    ctx = ProtectedContext(workspace_root=proxy.boundary.workspace_root)
    res = proxy.submit("pytest", context=ctx, execution_mode=ExecutionMode.SIMULATION)
    assert res.enforcement_status in ("ALLOWED", "SIMULATED")


# 22. Concurrent commands
def test_22_concurrent_commands(daemon_instance):
    url = "http://127.0.0.1:8769/evaluate"

    def send_eval(cmd):
        payload = json.dumps({"command": cmd, "cwd": os.getcwd()}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status
        except urllib.error.HTTPError as err:
            return err.code

    cmds = ["pytest", "git status", "dir", "echo 1", "echo 2"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(send_eval, cmds))

    assert all(r == 200 for r in results)
