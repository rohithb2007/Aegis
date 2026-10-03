import re
from enum import Enum
from typing import Tuple, Optional
from observer.events import AntigravityEvent, EventType
from .state import SessionState, CommandStatus


class WorkflowPhase(str, Enum):
    UNKNOWN = "UNKNOWN"
    RESEARCH = "RESEARCH"
    PLANNING = "PLANNING"
    IMPLEMENTATION = "IMPLEMENTATION"
    VERIFICATION = "VERIFICATION"
    DEBUGGING = "DEBUGGING"
    COMPLETION = "COMPLETION"


class PhaseDetector:
    """Deterministic, rule-based workflow phase detector."""

    # Keywords/patterns indicating verification commands
    VERIFICATION_PATTERNS = [
        r"pytest", r"npm\s+(run\s+)?test", r"npm\s+run\s+build", r"cargo\s+test",
        r"go\s+test", r"mvn\s+test", r"gradle\s+test", r"python\s+-m\s+unittest",
        r"vitest", r"jest", r"flake8", r"pylint", r"mypy", r"eslint"
    ]

    def detect(self, event: AntigravityEvent, state: SessionState) -> Tuple[WorkflowPhase, str]:
        """Evaluate event and current state to determine current workflow phase and reason."""
        ev_type = event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)

        # 1. Check for Task Completion
        if ev_type == EventType.TASK_COMPLETED.value:
            return WorkflowPhase.COMPLETION, "Task completion event detected"

        # 2. Check for Verification commands
        cmd_str = (event.command or (event.tool_args.get("CommandLine") if event.tool_args else "") or "").lower()
        if ev_type in [EventType.RUN_COMMAND.value, EventType.COMMAND_RESULT.value] and cmd_str:
            for pat in self.VERIFICATION_PATTERNS:
                if re.search(pat, cmd_str):
                    return WorkflowPhase.VERIFICATION, f"Verification command detected: '{cmd_str.strip()}'"

        # 3. Check for Debugging (Command failures, task failures, error results)
        if ev_type == EventType.TASK_FAILED.value:
            return WorkflowPhase.DEBUGGING, "Task failure detected"

        if ev_type == EventType.COMMAND_RESULT.value and event.result_summary:
            res_lower = event.result_summary.lower()
            if any(term in res_lower for term in ["failed", "error", "exception", "exit code 1", "exit code 2"]):
                return WorkflowPhase.DEBUGGING, f"Command failure/error detected: '{event.result_summary[:60]}'"

        # Check if last command in state failed
        if state.commands and state.commands[-1].status == CommandStatus.FAILURE:
            if ev_type == EventType.EDIT_FILE.value:
                return WorkflowPhase.DEBUGGING, "File edit following a failed command (debugging retry)"

        # 4. Check for Implementation (File modifications)
        if ev_type == EventType.EDIT_FILE.value:
            target = event.file_path or "file"
            return WorkflowPhase.IMPLEMENTATION, f"File edit detected: {target}"

        # 5. Check for Planning (Plan files or agent message context)
        if event.file_path and any(p in event.file_path.lower() for p in ["plan", "implementation_plan", "todo"]):
            return WorkflowPhase.PLANNING, f"Interaction with plan file detected: {event.file_path}"

        if ev_type == EventType.AGENT_MESSAGE.value and event.result_summary:
            msg_lower = event.result_summary.lower()
            if any(term in msg_lower for term in ["plan", "architecture", "design", "roadmap", "proposal"]):
                return WorkflowPhase.PLANNING, "Agent message indicates planning activity"

        # 6. Check for Research (Viewing files or listing directories)
        if ev_type in [EventType.VIEW_FILE.value, EventType.LIST_DIRECTORY.value]:
            if not state.modified_files:
                return WorkflowPhase.RESEARCH, f"File or directory inspection prior to edits ({ev_type})"
            return WorkflowPhase.RESEARCH, f"File/directory inspection: {event.file_path or 'unknown'}"

        # Fallback to current phase in state if valid, else UNKNOWN
        if state.current_phase and state.current_phase != WorkflowPhase.UNKNOWN.value:
            return WorkflowPhase(state.current_phase), state.phase_reason or "Maintaining previous active phase"

        return WorkflowPhase.UNKNOWN, "Insufficient event signals to determine phase"
