import os
import json
import urllib.request
import urllib.error
import pytest
from protected.daemon import AegisGatewayDaemon
from policy.approval import ApprovalManager, ApprovalStatus


def test_dashboard_build_artifacts_exist():
    """Verify that V1.1 Aegis Dashboard frontend build artifacts exist."""
    dash_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")
    dist_dir = os.path.join(dash_dir, "dist")
    index_html = os.path.join(dist_dir, "index.html")

    assert os.path.exists(dash_dir), "Dashboard source directory must exist"
    assert os.path.exists(dist_dir), "Dashboard production build dist folder must exist"
    assert os.path.exists(index_html), "Dashboard production index.html must exist"


def test_allowed_dashboard_origin_cors():
    """Verify that allowed dashboard origins receive exact CORS headers."""
    daemon = AegisGatewayDaemon(port=8798)
    daemon.start_in_background()

    try:
        req = urllib.request.Request("http://127.0.0.1:8798/status", headers={"Origin": "http://localhost:5173"})
        with urllib.request.urlopen(req) as resp:
            headers = dict(resp.headers)
            assert headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
            assert "GET" in headers.get("Access-Control-Allow-Methods", "")
            assert headers.get("Vary") == "Origin"

        req127 = urllib.request.Request("http://127.0.0.1:8798/status", headers={"Origin": "http://127.0.0.1:5173"})
        with urllib.request.urlopen(req127) as resp:
            headers = dict(resp.headers)
            assert headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:5173"
    finally:
        daemon.stop()


def test_untrusted_origin_cors_rejection():
    """Verify that arbitrary/untrusted origins do NOT receive permissive CORS access."""
    daemon = AegisGatewayDaemon(port=8798)
    daemon.start_in_background()

    try:
        req = urllib.request.Request("http://127.0.0.1:8798/status", headers={"Origin": "http://evil-attacker.com"})
        with urllib.request.urlopen(req) as resp:
            headers = dict(resp.headers)
            assert "Access-Control-Allow-Origin" not in headers
            assert headers.get("Access-Control-Allow-Origin") != "*"
            assert headers.get("Access-Control-Allow-Origin") != "http://evil-attacker.com"
    finally:
        daemon.stop()


def test_options_preflight_behavior():
    """Verify OPTIONS preflight returns 204 for allowed origin and 403 for untrusted origin."""
    daemon = AegisGatewayDaemon(port=8798)
    daemon.start_in_background()

    try:
        # Allowed origin preflight
        req_allowed = urllib.request.Request(
            "http://127.0.0.1:8798/status",
            headers={"Origin": "http://localhost:5173"},
            method="OPTIONS"
        )
        with urllib.request.urlopen(req_allowed) as resp:
            assert resp.status == 204
            assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"

        # Untrusted origin preflight
        req_untrusted = urllib.request.Request(
            "http://127.0.0.1:8798/status",
            headers={"Origin": "http://malicious-site.com"},
            method="OPTIONS"
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req_untrusted)
        assert exc_info.value.code == 403
        assert "Access-Control-Allow-Origin" not in exc_info.value.headers
    finally:
        daemon.stop()


def test_post_approve_backend_protection():
    """Verify POST /approve remains protected by backend approval logic."""
    daemon = AegisGatewayDaemon(port=8798)
    daemon.start_in_background()

    try:
        # Non-existent request ID
        data = json.dumps({"request_id": "req-nonexistent"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8798/approve", data=data, headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 404

        # Valid pending request
        req_obj = daemon.approval_manager.create_request(
            command="git push --force origin main",
            risk_classification="HIGH_RISK",
            risk_score=80,
            capabilities=["GIT_REMOTE"],
            ai_verdict="QUESTIONABLE",
            explanation="Remote push",
            policy_reasons=[]
        )
        data_valid = json.dumps({"request_id": req_obj.request_id}).encode("utf-8")
        req_valid = urllib.request.Request("http://127.0.0.1:8798/approve", data=data_valid, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req_valid) as resp:
            assert resp.status == 200
            res_json = json.loads(resp.read().decode("utf-8"))
            assert res_json["status"] == "APPROVED"
    finally:
        daemon.stop()


def test_post_deny_backend_protection():
    """Verify POST /deny remains protected by backend approval logic."""
    daemon = AegisGatewayDaemon(port=8798)
    daemon.start_in_background()

    try:
        req_obj = daemon.approval_manager.create_request(
            command="git push --force origin test",
            risk_classification="HIGH_RISK",
            risk_score=80,
            capabilities=["GIT_REMOTE"],
            ai_verdict="QUESTIONABLE",
            explanation="Remote push",
            policy_reasons=[]
        )
        data = json.dumps({"request_id": req_obj.request_id}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8798/deny", data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res_json = json.loads(resp.read().decode("utf-8"))
            assert res_json["status"] == "DENIED"
    finally:
        daemon.stop()


def test_post_protection_human_only_semantics():
    """Verify POST /protection rejects agent-context payloads with HTTP 403 Forbidden."""
    daemon = AegisGatewayDaemon(port=8798)
    daemon.start_in_background()

    try:
        # Agent payload attempting to turn protection OFF
        data = json.dumps({"state": "OFF", "session_id": "agent-session-123", "task_id": "task-1"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8798/protection", data=data, headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 403

        # Human payload succeeds
        data_human = json.dumps({"state": "ON"}).encode("utf-8")
        req_human = urllib.request.Request("http://127.0.0.1:8798/protection", data=data_human, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req_human) as resp:
            assert resp.status == 200
    finally:
        daemon.stop()


def test_post_shutdown_releases_port():
    """Verify that POST /shutdown cleanly stops server and releases port."""
    import time
    daemon = AegisGatewayDaemon(port=8799)
    daemon.start_in_background()
    time.sleep(0.1)

    req = urllib.request.Request("http://127.0.0.1:8799/shutdown", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        res_json = json.loads(resp.read().decode("utf-8"))
        assert res_json["status"] == "SHUTTING_DOWN"

    time.sleep(0.3)
    req_check = urllib.request.Request("http://127.0.0.1:8799/status")
    with pytest.raises((urllib.error.URLError, ConnectionResetError, OSError)):
        urllib.request.urlopen(req_check, timeout=1.0)

