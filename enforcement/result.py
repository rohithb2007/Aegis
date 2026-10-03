from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from .models import EnforcementStatus, ExecutionMode


@dataclass
class CommandResult:
    command: str
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
        }


@dataclass
class EnforcementResult:
    enforcement_id: str
    status: EnforcementStatus
    execution_mode: ExecutionMode
    policy_decision: str
    policy_reasons: List[str] = field(default_factory=list)
    approval_id: Optional[str] = None
    approval_status: Optional[str] = None
    command_result: Optional[CommandResult] = None
    explanation: str = ""
    timestamp: Optional[str] = None
    command: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enforcement_id": self.enforcement_id,
            "status": self.status.value if isinstance(self.status, EnforcementStatus) else str(self.status),
            "execution_mode": self.execution_mode.value if isinstance(self.execution_mode, ExecutionMode) else str(self.execution_mode),
            "policy_decision": self.policy_decision,
            "policy_reasons": self.policy_reasons,
            "approval_id": self.approval_id,
            "approval_status": self.approval_status,
            "command_result": self.command_result.to_dict() if self.command_result else None,
            "explanation": self.explanation,
            "timestamp": self.timestamp,
            "command": self.command,
        }

    def render_console(self) -> str:
        status_str = self.status.value if isinstance(self.status, EnforcementStatus) else str(self.status)
        mode_str = self.execution_mode.value if isinstance(self.execution_mode, ExecutionMode) else str(self.execution_mode)

        output_summary = "N/A"
        if self.command_result:
            if self.command_result.stdout:
                output_summary = self.command_result.stdout.strip()
            elif self.command_result.stderr:
                output_summary = f"[STDERR] {self.command_result.stderr.strip()}"
            elif self.command_result.error_message:
                output_summary = f"[ERROR] {self.command_result.error_message}"

        lines = [
            "====================================",
            "      AEGIS ENFORCEMENT ENGINE      ",
            "====================================",
            f"Enforcement ID:\n  {self.enforcement_id}",
            f"\nCommand:\n  {self.command or (self.command_result.command if self.command_result else 'N/A')}",
            f"\nPolicy Decision:\n  {self.policy_decision}",
            f"\nApproval Status:\n  {self.approval_status or 'N/A'}",
            f"\nEnforcement Status:\n  {status_str}",
            f"\nExecution Mode:\n  {mode_str}",
            f"\nExplanation:\n  {self.explanation}",
            f"\nCommand Execution Output:\n  {output_summary}",
            "\nNotice:\n  Aegis operates in simulation/control mode. Runtime pre-execution hooks remain advisory.",
            "====================================",
        ]
        return "\n".join(lines)
