import pytest
from enforcement.models import EnforcementStatus, ExecutionMode, EnforcementRequest
from enforcement.result import CommandResult, EnforcementResult


def test_enforcement_request_creation():
    req = EnforcementRequest.create(
        command="git status",
        policy_decision="ALLOW",
        policy_severity="INFORMATIONAL",
        v03_risk="SAFE",
        execution_mode=ExecutionMode.SIMULATION,
    )
    assert req.enforcement_id.startswith("enf-")
    assert req.command == "git status"
    assert req.policy_decision == "ALLOW"
    assert req.execution_mode == ExecutionMode.SIMULATION

    d = req.to_dict()
    assert d["enforcement_id"] == req.enforcement_id
    assert d["command"] == "git status"
    assert d["execution_mode"] == "SIMULATION"


def test_command_result_and_enforcement_result():
    cmd_res = CommandResult(
        command="npm test",
        exit_code=0,
        stdout="All 10 tests passed",
        stderr="",
        execution_time_ms=120.5
    )
    res = EnforcementResult(
        enforcement_id="enf-12345",
        status=EnforcementStatus.ALLOWED,
        execution_mode=ExecutionMode.CONTROLLED,
        policy_decision="ALLOW",
        policy_reasons=["Safe project command"],
        command_result=cmd_res,
        explanation="Executed cleanly in controlled mode.",
        command="npm test"
    )

    assert res.status == EnforcementStatus.ALLOWED
    assert res.command_result.exit_code == 0

    d = res.to_dict()
    assert d["enforcement_id"] == "enf-12345"
    assert d["command_result"]["stdout"] == "All 10 tests passed"

    console = res.render_console()
    assert "AEGIS ENFORCEMENT ENGINE" in console
    assert "ALLOWED" in console
    assert "npm test" in console
