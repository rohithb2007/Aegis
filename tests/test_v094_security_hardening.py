import os
import json
import tempfile
import pytest
from protected.protection import ProtectionManager
from protected.proxy import CommandProxy
from protected.daemon import AegisGatewayDaemon
from protected.models import ProtectedContext, GatewayStatus
from policy.approval import ApprovalManager, ApprovalStatus, normalize_command
from policy.engine import PolicyEngine
from policy.rules import PolicyRuleEngine
from policy.models import PolicyDecision, PolicySeverity
from safety.models import SafetyAssessment, SafetyClassification
from enforcement.gate import EnforcementGate
from enforcement.models import ExecutionMode, EnforcementStatus


def create_test_request(
    mgr: ApprovalManager,
    cmd: str,
    risk_classification="HIGH_RISK",
    explanation="Test review requirement",
):
    cls_str = (
        risk_classification.value
        if hasattr(risk_classification, "value")
        else str(risk_classification)
    )
    return mgr.create_request(
        command=cmd,
        risk_classification=cls_str,
        risk_score=80,
        capabilities=["TEST_CAPABILITY"],
        ai_verdict="NEEDS_HUMAN_REVIEW",
        explanation=explanation,
        policy_reasons=[],
    )


class TestV094SecurityHardening:
    """Comprehensive test suite for Aegis V0.9.4 Security & Reliability Hardening."""

    # ----------------------------------------------------
    # PHASE 2 & INVARIANT TESTS
    # ----------------------------------------------------

    def test_invariant_a_protection_on_gateway_unavailable_fails_closed(self):
        """Invariant A: Protection ON + Gateway unavailable => Fail Closed."""
        proxy = CommandProxy()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(proxy.safety_analyzer, "analyze", lambda *a, **k: 1 / 0)
            res = proxy.submit("git push origin main")
            assert res.gateway_status == GatewayStatus.FAILED_GATEWAY
            assert res.enforcement_status == "FAILED"
            assert res.policy_decision == "ERROR"

    def test_invariant_b_protection_off_human_controlled_only(self):
        """Invariant B: Antigravity agent cannot disable protection via Gateway API."""
        daemon = AegisGatewayDaemon(port=8891)
        daemon.start_in_background()
        try:
            import urllib.request
            import urllib.error

            url = f"http://127.0.0.1:{daemon.port}/protection/set"

            # Agent payload attempt
            agent_payload = json.dumps({
                "state": "OFF",
                "session_id": "session-123",
                "task_id": "task-456",
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=agent_payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 403

            # Verify protection is still ON
            assert daemon.protection_manager.is_protection_on() is True
        finally:
            daemon.stop()

    def test_invariant_c_agent_cannot_disable_protection_via_interceptor(self):
        """Invariant C: Antigravity cannot disable protection through an intercepted command (Rule POL-000)."""
        dec, sev, reasons = PolicyRuleEngine.evaluate("--protection-off")
        assert dec == PolicyDecision.BLOCK
        assert sev == PolicySeverity.CRITICAL
        assert reasons[0].rule_id == "POL-000"

        dec2, sev2, _ = PolicyRuleEngine.evaluate("Remove-Item config/protection_state.json")
        assert dec2 == PolicyDecision.BLOCK
        assert sev2 == PolicySeverity.CRITICAL

    def test_invariant_d_critical_actions_cannot_be_approved(self):
        """Invariant D: CRITICAL actions cannot be overridden by human approval."""
        approval_mgr = ApprovalManager()
        req = create_test_request(
            approval_mgr,
            "rm -rf /",
            risk_classification=SafetyClassification.CRITICAL,
            explanation="Critical delete",
        )
        approval_mgr.approve(req.request_id)

        # Evaluate through policy engine
        engine = PolicyEngine(approval_manager=approval_mgr)
        ass = engine.evaluate("rm -rf /")

        # Must still be BLOCK despite approved status in ApprovalManager!
        assert ass.decision == PolicyDecision.BLOCK
        assert ass.severity == PolicySeverity.CRITICAL

    def test_invariant_e_and_f_exact_command_binding(self):
        """Invariant E & F: Approval is not blanket; materially different command requires new approval."""
        approval_mgr = ApprovalManager()
        cmd1 = "git push --force origin main"
        cmd2 = "git push --force origin feature-branch"

        req = create_test_request(
            approval_mgr,
            cmd1,
            risk_classification=SafetyClassification.HIGH_RISK,
            explanation="Force push main",
        )
        approval_mgr.approve(req.request_id)

        # Exact command matches
        found1 = approval_mgr.find_approved_request(cmd1)
        assert found1 is not None
        assert found1.request_id == req.request_id

        # Different branch command fails to match approval
        found2 = approval_mgr.find_approved_request(cmd2)
        assert found2 is None

    def test_invariant_g_denied_expired_cancelled_cannot_execute(self):
        """Invariant G: Denied/expired/cancelled approvals cannot authorize execution."""
        approval_mgr = ApprovalManager()
        cmd = "git push --force origin main"

        # Denied
        req1 = create_test_request(approval_mgr, cmd, SafetyClassification.HIGH_RISK)
        approval_mgr.deny(req1.request_id)
        assert approval_mgr.find_approved_request(cmd) is None

        # Cancelled
        req2 = create_test_request(approval_mgr, cmd, SafetyClassification.HIGH_RISK)
        approval_mgr.cancel(req2.request_id)
        assert approval_mgr.find_approved_request(cmd) is None

        # Expired
        req3 = create_test_request(approval_mgr, cmd, SafetyClassification.HIGH_RISK)
        approval_mgr.mark_expired(req3.request_id)
        assert approval_mgr.find_approved_request(cmd) is None

    def test_invariant_h_approval_cannot_downgrade_critical_block(self):
        """Invariant H: Approval state cannot silently downgrade a CRITICAL security decision."""
        gate = EnforcementGate()
        approval_mgr = gate.approval_manager

        req = create_test_request(
            approval_mgr,
            "drop database production",
            risk_classification=SafetyClassification.CRITICAL,
            explanation="DB Drop",
        )
        approval_mgr.approve(req.request_id)

        # Policy engine evaluates CRITICAL drop database
        engine = PolicyEngine(approval_manager=approval_mgr)
        pol_ass = engine.evaluate("drop database production")

        gate_res = gate.process(pol_ass)
        assert gate_res.status == EnforcementStatus.BLOCKED

    def test_invariant_i_secrets_redacted_in_telemetry(self):
        """Invariant I: Secrets must not appear in telemetry/audit/log output."""
        proxy = CommandProxy()
        secret_cmd = "git push https://ghp_1234567890abcdefghijklmnopqrstuvwxyz@github.com/repo.git"
        res = proxy.submit(secret_cmd)

        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in res.command
        assert "[REDACTED_SECRET_KEY]" in res.command or "[REDACTED_BEARER_TOKEN]" in res.command or "[REDACTED" in res.command

    def test_invariant_j_unexpected_error_never_becomes_allow(self):
        """Invariant J: Unexpected errors must never silently become ALLOW."""
        proxy = CommandProxy()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(proxy.policy_engine, "evaluate", lambda *a, **k: 1 / 0)
            res = proxy.submit("ls")
            assert res.gateway_status == GatewayStatus.FAILED_GATEWAY
            assert res.policy_decision == "ERROR"
            assert res.enforcement_status == "FAILED"

    # ----------------------------------------------------
    # PHASE 3 — APPROVAL STATE MACHINE ROBUSTNESS
    # ----------------------------------------------------

    def test_approval_state_transitions(self):
        """Verify strict state transitions in ApprovalManager."""
        mgr = ApprovalManager()
        req = create_test_request(mgr, "git push --force", SafetyClassification.HIGH_RISK)
        assert req.status == ApprovalStatus.PENDING

        # Transition PENDING -> APPROVED
        app_req = mgr.approve(req.request_id)
        assert app_req.status == ApprovalStatus.APPROVED

        # Transition APPROVED -> APPROVED (idempotent returns request)
        app_req_again = mgr.approve(req.request_id)
        assert app_req_again is not None
        assert app_req_again.status == ApprovalStatus.APPROVED

        # Transition APPROVED -> DENIED (invalid state transition attempt returns None)
        deny_req = mgr.deny(req.request_id)
        assert deny_req is None

    def test_denied_state_cannot_be_approved(self):
        """Verify DENIED request cannot be subsequently APPROVED."""
        mgr = ApprovalManager()
        req = create_test_request(mgr, "git push --force", SafetyClassification.HIGH_RISK)
        mgr.deny(req.request_id)

        res = mgr.approve(req.request_id)
        assert res is None
        assert mgr.get_request(req.request_id).status == ApprovalStatus.DENIED

    # ----------------------------------------------------
    # PHASE 4 — GATEWAY HARDENING
    # ----------------------------------------------------

    def test_gateway_http_hardening(self):
        """Verify Gateway HTTP endpoint validation and unsupported method rejection."""
        daemon = AegisGatewayDaemon(port=8892)
        daemon.start_in_background()
        try:
            import urllib.request
            import urllib.error

            base_url = f"http://127.0.0.1:{daemon.port}"

            # Test PUT method rejection
            req_put = urllib.request.Request(
                f"{base_url}/evaluate",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="PUT",
            )
            with pytest.raises(urllib.error.HTTPError) as exc_put:
                urllib.request.urlopen(req_put)
            assert exc_put.value.code in (405, 501)

            # Test DELETE method rejection
            req_del = urllib.request.Request(f"{base_url}/evaluate", method="DELETE")
            with pytest.raises(urllib.error.HTTPError) as exc_del:
                urllib.request.urlopen(req_del)
            assert exc_del.value.code in (405, 501)

            # Test Invalid JSON body on /evaluate fails safely
            req_bad_json = urllib.request.Request(
                f"{base_url}/evaluate",
                data=b"NOT_VALID_JSON{",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req_bad_json)
            assert resp.getcode() in (200, 202, 403, 400)
        finally:
            daemon.stop()

    # ----------------------------------------------------
    # PHASE 5 — PROTECTION STATE HARDENING
    # ----------------------------------------------------

    def test_corrupted_protection_file_defaults_to_on(self):
        """Verify corrupted or invalid JSON in protection_state.json defaults safely to ON."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            mgr = ProtectionManager(config_dir=tmp_dir)
            state_file = os.path.join(tmp_dir, "protection_state.json")

            # Case 1: Corrupted JSON
            with open(state_file, "w", encoding="utf-8") as f:
                f.write("{invalid json content...")
            assert mgr.is_protection_on() is True
            assert mgr.get_status_dict()["status"] == "ON"

            # Case 2: Invalid non-boolean enabled field
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({"enabled": "false_string"}, f)
            assert mgr.is_protection_on() is True

            # Case 3: Missing file
            os.remove(state_file)
            assert mgr.is_protection_on() is True

    # ----------------------------------------------------
    # PHASE 7 — COMMAND NORMALIZATION
    # ----------------------------------------------------

    def test_command_normalization_equivalence(self):
        """Verify normalize_command behavior for syntactic vs semantic changes."""
        # Syntactic variations (slashes, spacing, cmd case) -> Same normalized identity
        norm1 = normalize_command(r"GIT  push   --dry-run   origin\main")
        norm2 = normalize_command("git push --dry-run origin/main")
        assert norm1 == norm2

        # Material semantic variations -> Different identity
        norm_branch_a = normalize_command("git push origin branch-a")
        norm_branch_b = normalize_command("git push origin branch-b")
        assert norm_branch_a != norm_branch_b
