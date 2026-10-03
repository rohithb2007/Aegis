import pytest
import sys
from enforcement.models import EnforcementStatus, ExecutionMode, EnforcementRequest
from enforcement.result import EnforcementResult
from enforcement.executor import SimulationExecutor, ControlledExecutor, ExecutorFactory


def test_simulation_executor_never_executes_real_processes():
    sim = SimulationExecutor()
    req = EnforcementRequest.create(
        command="rm -rf /",
        policy_decision="ALLOW",
        execution_mode=ExecutionMode.SIMULATION
    )
    gate_res = EnforcementResult(
        enforcement_id=req.enforcement_id,
        status=EnforcementStatus.SIMULATED,
        execution_mode=ExecutionMode.SIMULATION,
        policy_decision="ALLOW",
        command="rm -rf /"
    )

    final_res = sim.execute(req, gate_res)
    assert final_res.status == EnforcementStatus.SIMULATED
    assert final_res.command_result is not None
    assert "[SIMULATION MODE]" in final_res.command_result.stdout
    # No actual OS process was executed


def test_simulation_executor_skips_unallowed():
    sim = SimulationExecutor()
    req = EnforcementRequest.create(
        command="git push --force",
        policy_decision="REVIEW",
        execution_mode=ExecutionMode.SIMULATION
    )
    gate_res = EnforcementResult(
        enforcement_id=req.enforcement_id,
        status=EnforcementStatus.WAITING_FOR_APPROVAL,
        execution_mode=ExecutionMode.SIMULATION,
        policy_decision="REVIEW",
        explanation="Waiting for approval",
        command="git push --force"
    )

    final_res = sim.execute(req, gate_res)
    assert final_res.command_result.exit_code == -1
    assert "skipped" in final_res.command_result.stderr.lower()


def test_controlled_executor_safe_execution():
    executor = ControlledExecutor(timeout_seconds=5.0)
    req = EnforcementRequest.create(
        command="echo Hello Aegis",
        policy_decision="ALLOW",
        execution_mode=ExecutionMode.CONTROLLED
    )
    gate_res = EnforcementResult(
        enforcement_id=req.enforcement_id,
        status=EnforcementStatus.ALLOWED,
        execution_mode=ExecutionMode.CONTROLLED,
        policy_decision="ALLOW",
        command="echo Hello Aegis"
    )

    final_res = executor.execute(req, gate_res)
    assert final_res.status == EnforcementStatus.ALLOWED
    assert final_res.command_result is not None
    assert final_res.command_result.exit_code == 0
    assert "Hello Aegis" in final_res.command_result.stdout


def test_controlled_executor_refuses_blocked_command():
    executor = ControlledExecutor(timeout_seconds=5.0)
    req = EnforcementRequest.create(
        command="rm -rf /",
        policy_decision="BLOCK",
        execution_mode=ExecutionMode.CONTROLLED
    )
    gate_res = EnforcementResult(
        enforcement_id=req.enforcement_id,
        status=EnforcementStatus.BLOCKED,
        execution_mode=ExecutionMode.CONTROLLED,
        policy_decision="BLOCK",
        explanation="Blocked by policy",
        command="rm -rf /"
    )

    final_res = executor.execute(req, gate_res)
    assert final_res.status == EnforcementStatus.BLOCKED
    assert final_res.command_result.exit_code == -1
    assert "Refused execution" in final_res.command_result.stderr


def test_executor_factory():
    sim_exec = ExecutorFactory.get_executor(ExecutionMode.SIMULATION)
    assert isinstance(sim_exec, SimulationExecutor)

    ctrl_exec = ExecutorFactory.get_executor(ExecutionMode.CONTROLLED)
    assert isinstance(ctrl_exec, ControlledExecutor)
