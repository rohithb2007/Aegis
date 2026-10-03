import os
import sys
import time
import subprocess
import shlex
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from .models import EnforcementStatus, ExecutionMode, EnforcementRequest
from .result import CommandResult, EnforcementResult

logger = logging.getLogger("AegisCommandExecutor")


class CommandExecutor(ABC):
    """Abstract Command Executor for Aegis V0.7 Enforcement Layer."""

    @abstractmethod
    def execute(
        self,
        request: EnforcementRequest,
        gate_result: EnforcementResult,
        cwd: Optional[str] = None,
    ) -> EnforcementResult:
        pass


class SimulationExecutor(CommandExecutor):
    """Default simulation executor. Never executes real OS processes."""

    def execute(
        self,
        request: EnforcementRequest,
        gate_result: EnforcementResult,
        cwd: Optional[str] = None,
    ) -> EnforcementResult:
        cmd = request.command or gate_result.command or ""
        status_val = gate_result.status.value if isinstance(gate_result.status, EnforcementStatus) else str(gate_result.status)

        if status_val in (EnforcementStatus.ALLOWED.value, EnforcementStatus.SIMULATED.value):
            gate_result.status = EnforcementStatus.SIMULATED
            gate_result.command_result = CommandResult(
                command=cmd,
                exit_code=0,
                stdout=f"[SIMULATION MODE] Command '{cmd}' cleared by policy and gate. Execution simulated cleanly.",
                stderr="",
                execution_time_ms=0.0,
            )
            gate_result.explanation = (
                f"Simulation mode: command '{cmd}' evaluated as safe/approved. Real execution was simulated."
            )
        else:
            gate_result.command_result = CommandResult(
                command=cmd,
                exit_code=-1,
                stdout="",
                stderr=f"[SIMULATION MODE] Command execution skipped because status is {status_val}.",
                execution_time_ms=0.0,
                error_message=gate_result.explanation,
            )

        return gate_result


class ControlledExecutor(CommandExecutor):
    """Controlled executor performing real subprocess execution under strict constraints."""

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds

    def execute(
        self,
        request: EnforcementRequest,
        gate_result: EnforcementResult,
        cwd: Optional[str] = None,
    ) -> EnforcementResult:
        cmd = request.command or gate_result.command or ""
        status_val = gate_result.status.value if isinstance(gate_result.status, EnforcementStatus) else str(gate_result.status)

        # SECURITY INVARIANT: Refuse execution if status is not ALLOWED or SIMULATED
        if status_val not in (EnforcementStatus.ALLOWED.value, EnforcementStatus.SIMULATED.value):
            logger.warning(f"[Aegis Executor Security] Refusing execution of command '{cmd}' with status {status_val}")
            gate_result.command_result = CommandResult(
                command=cmd,
                exit_code=-1,
                stdout="",
                stderr=f"Refused execution: Enforcement status is {status_val}",
                execution_time_ms=0.0,
                error_message=f"Execution blocked by gate status '{status_val}'",
            )
            return gate_result

        work_dir = cwd or os.getcwd()
        start_time = time.perf_counter()

        try:
            # Use shell=True selectively on Windows for shell builtins if string, or list args on POSIX
            use_shell = sys.platform == "win32"
            proc = subprocess.run(
                cmd,
                shell=use_shell,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            gate_result.status = EnforcementStatus.ALLOWED
            gate_result.command_result = CommandResult(
                command=cmd,
                exit_code=proc.returncode,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                execution_time_ms=elapsed_ms,
            )
            if proc.returncode == 0:
                gate_result.explanation = f"Command executed successfully (exit code 0 in {elapsed_ms}ms)."
            else:
                gate_result.explanation = f"Command executed with non-zero exit code {proc.returncode} in {elapsed_ms}ms."

        except subprocess.TimeoutExpired as err:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            gate_result.status = EnforcementStatus.FAILED
            gate_result.command_result = CommandResult(
                command=cmd,
                exit_code=124,
                stdout=err.stdout or "" if hasattr(err, "stdout") and err.stdout else "",
                stderr=err.stderr or "" if hasattr(err, "stderr") and err.stderr else "Process execution timed out.",
                execution_time_ms=elapsed_ms,
                error_message=f"Command execution timed out after {self.timeout_seconds}s.",
            )
            gate_result.explanation = f"Execution failed: command timed out after {self.timeout_seconds} seconds."

        except Exception as err:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            gate_result.status = EnforcementStatus.FAILED
            gate_result.command_result = CommandResult(
                command=cmd,
                exit_code=-1,
                stdout="",
                stderr=str(err),
                execution_time_ms=elapsed_ms,
                error_message=str(err),
            )
            gate_result.explanation = f"Execution failed due to OS/process creation error: {err}"

        return gate_result


class ExecutorFactory:
    """Factory creating appropriate CommandExecutor based on ExecutionMode."""

    @staticmethod
    def get_executor(mode: ExecutionMode = ExecutionMode.SIMULATION, timeout_seconds: float = 30.0) -> CommandExecutor:
        if mode == ExecutionMode.SIMULATION:
            return SimulationExecutor()
        elif mode in (ExecutionMode.CONTROLLED, ExecutionMode.LIVE):
            return ControlledExecutor(timeout_seconds=timeout_seconds)
        return SimulationExecutor()
