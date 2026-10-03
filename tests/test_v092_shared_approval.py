import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
import pytest
from protected.daemon import AegisGatewayDaemon
from protected.models import ProtectedContext, GatewayStatus
from policy.approval import ApprovalManager, ApprovalStatus
from enforcement.models import ExecutionMode


@pytest.fixture
def daemon_instance_v092():
    """Fixture running AegisGatewayDaemon on port 8771 for testing V0.9.2."""
    daemon = AegisGatewayDaemon(port=8771)
    daemon.start_in_background()
    time.sleep(0.3)
    yield daemon
    daemon.stop()


# 1, 2, 3. Gateway creates pending request -> CLI --approve -> Gateway request becomes APPROVED -> Resubmitted command passes
def test_v092_approval_workflow_via_gateway(daemon_instance_v092):
    url_eval = "http://127.0.0.1:8771/evaluate"
    cmd_str = "git push --force origin main"
    payload = json.dumps({"command": cmd_str, "cwd": os.getcwd()}).encode("utf-8")
    req_eval = urllib.request.Request(url_eval, data=payload, headers={"Content-Type": "application/json"})

    app_id = None
    try:
        with urllib.request.urlopen(req_eval) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            app_id = data["approval_id"]
    except urllib.error.HTTPError as err:
        assert err.code == 202
        data = json.loads(err.read().decode("utf-8"))
        app_id = data["approval_id"]

    assert app_id is not None
    assert daemon_instance_v092.approval_manager.get_request(app_id).status == ApprovalStatus.PENDING

    # Run CLI in separate subprocess: python main.py --port 8771 --approve <app_id>
    proc = subprocess.run(
        [sys.executable, "main.py", "--port", "8771", "--approve", app_id],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    assert "set to APPROVED via Aegis Gateway" in proc.stdout

    # Verify Gateway's in-memory approval manager state
    assert daemon_instance_v092.approval_manager.get_request(app_id).status == ApprovalStatus.APPROVED

    # Resubmit command -> Gateway must return 200 PERMITTED
    with urllib.request.urlopen(req_eval) as resp:
        data_resub = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert data_resub["gateway_status"] == "PERMITTED"


# 4, 5. Gateway creates pending request -> CLI --deny -> Gateway request becomes DENIED -> Resubmitted command fails (403)
def test_v092_denial_workflow_via_gateway(daemon_instance_v092):
    url_eval = "http://127.0.0.1:8771/evaluate"
    cmd_str = "git push --force origin feature-deny"
    payload = json.dumps({"command": cmd_str, "cwd": os.getcwd()}).encode("utf-8")
    req_eval = urllib.request.Request(url_eval, data=payload, headers={"Content-Type": "application/json"})

    app_id = None
    try:
        with urllib.request.urlopen(req_eval) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            app_id = data["approval_id"]
    except urllib.error.HTTPError as err:
        assert err.code == 202
        data = json.loads(err.read().decode("utf-8"))
        app_id = data["approval_id"]

    assert app_id is not None

    # Run CLI in separate subprocess: python main.py --port 8771 --deny <app_id>
    proc = subprocess.run(
        [sys.executable, "main.py", "--port", "8771", "--deny", app_id],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    assert "set to DENIED via Aegis Gateway" in proc.stdout

    # Verify Gateway's in-memory approval manager state
    assert daemon_instance_v092.approval_manager.get_request(app_id).status == ApprovalStatus.DENIED

    # Resubmit command -> Gateway must return 403 REJECTED_POLICY
    try:
        with urllib.request.urlopen(req_eval) as resp:
            pytest.fail("Denied command must be rejected with HTTP 403")
    except urllib.error.HTTPError as err:
        assert err.code == 403
        data_resub = json.loads(err.read().decode("utf-8"))
        assert data_resub["gateway_status"] == "REJECTED_POLICY"


# 6. Unknown request ID returns error (404)
def test_v092_unknown_request_id_returns_error(daemon_instance_v092):
    proc = subprocess.run(
        [sys.executable, "main.py", "--port", "8771", "--approve", "req-bogus999"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 1
    assert "not found or not in PENDING status" in proc.stdout or "not found" in proc.stderr


# 7. Gateway unavailable returns clear error
def test_v092_gateway_unavailable_returns_error():
    # Use non-existent gateway port 59998
    proc = subprocess.run(
        [sys.executable, "main.py", "--port", "59998", "--approve", "req-test"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode != 0
    assert "Aegis Gateway unavailable" in proc.stdout or "Aegis Gateway unavailable" in proc.stderr
    assert "Approval action was NOT performed" in proc.stdout or "Approval action was NOT performed" in proc.stderr


# 8. CLI --approval-status and --approval-list query gateway
def test_v092_cli_approval_status_and_list(daemon_instance_v092):
    # Create pending request
    url_eval = "http://127.0.0.1:8771/evaluate"
    payload = json.dumps({"command": "git push --force origin branch-list", "cwd": os.getcwd()}).encode("utf-8")
    req_eval = urllib.request.Request(url_eval, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req_eval)
    except urllib.error.HTTPError:
        pass

    # CLI approval status
    proc_stat = subprocess.run(
        [sys.executable, "main.py", "--port", "8771", "--approval-status"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc_stat.returncode == 0
    assert "Gateway Service:  CONNECTED" in proc_stat.stdout
    assert "Pending:          1" in proc_stat.stdout

    # CLI approval list
    proc_list = subprocess.run(
        [sys.executable, "main.py", "--port", "8771", "--approval-list"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc_list.returncode == 0
    assert "git push --force origin branch-list" in proc_list.stdout


# 9. Critical BLOCK remains impossible to override
def test_v092_critical_block_impossible_to_override(daemon_instance_v092):
    url_eval = "http://127.0.0.1:8771/evaluate"
    payload = json.dumps({"command": "rm -rf /", "cwd": os.getcwd()}).encode("utf-8")
    req_eval = urllib.request.Request(url_eval, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req_eval) as resp:
            pytest.fail("rm -rf / must return 403")
    except urllib.error.HTTPError as err:
        assert err.code == 403
        data = json.loads(err.read().decode("utf-8"))
        assert data["policy_decision"] == "BLOCK"
        # Ensure no approval_id was generated for BLOCK
        assert data["approval_id"] is None
