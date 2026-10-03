import re
from typing import Optional, Dict, Any
from observer.events import AntigravityEvent, EventType
from .state import SessionState, CommandStatus


class GoalTracker:
    """Deterministic, rule-based goal extractor (No LLM)."""

    # Patterns for detecting task/goal descriptions in messages
    GOAL_PATTERNS = [
        r"(?:goal|task|objective)\s*:\s*([^\n\.]+)",
        r"(?:implement|build|create|add|fix|refactor|debug|test)\s+([^\n\.]+)",
    ]

    def extract_goal(self, event: AntigravityEvent, current_goal: Optional[str] = None) -> Optional[str]:
        """Extract goal string from agent message or task content if deterministically present."""
        if current_goal and current_goal != "Unknown":
            return current_goal

        text_to_search = ""
        if event.event_type == EventType.AGENT_MESSAGE and event.result_summary:
            text_to_search = event.result_summary
        elif event.event_type in [EventType.TASK_STARTED, EventType.TASK_COMPLETED] and event.result_summary:
            text_to_search = event.result_summary

        if not text_to_search:
            return current_goal

        for pat in self.GOAL_PATTERNS:
            match = re.search(pat, text_to_search, re.IGNORECASE)
            if match:
                goal_str = match.group(1).strip(" :.-")
                if len(goal_str) > 5:
                    return goal_str[:100]

        return current_goal


class ContextSnapshot:
    """Formats SessionState into concise human-readable text snapshots and dictionaries."""

    @staticmethod
    def render_console(state: SessionState) -> str:
        """Render a clean ASCII human-readable session summary box."""
        sess_short = (state.session_id[:8] + "...") if state.session_id else "None"
        task = state.active_task_id or "None"
        status = state.task_status or ("ACTIVE" if state.active_task_id else "IDLE")
        goal = state.current_goal or "Unknown"
        phase = state.current_phase or "UNKNOWN"
        reason = state.phase_reason or "N/A"

        inspected_cnt = len(state.inspected_files)
        modified_cnt = len(state.modified_files)

        cmd_total = len(state.commands)
        last_cmd = state.commands[-1].command if state.commands else "None"
        last_res = state.commands[-1].status.value if (state.commands and state.commands[-1].status) else "N/A"

        err_total = len(state.errors)

        recent_acts = [
            e.event_type.value if isinstance(e.event_type, EventType) else str(e.event_type)
            for e in state.recent_events[-3:]
        ]
        recent_acts_str = "\n  ".join(reversed(recent_acts)) if recent_acts else "None"

        lines = [
            "+-------------- AEGIS --------------+",
            "| Antigravity Observer + Context   |",
            "+-----------------------------------+",
            f"Session: {sess_short}",
            f"Task:    {task}",
            f"Status:  {status}",
            "",
            "Goal:",
            f"  {goal}",
            "",
            "Phase:",
            f"  {phase}",
            "Reason:",
            f"  {reason}",
            "",
            "Files:",
            f"  Inspected: {inspected_cnt}",
            f"  Modified:  {modified_cnt}",
            "",
            "Commands:",
            f"  Total:  {cmd_total}",
            f"  Last:   {last_cmd}",
            f"  Result: {last_res}",
            "",
            f"Errors:",
            f"  {err_total}",
            "",
            "Recent activity:",
            f"  {recent_acts_str}"
        ]
        return "\n".join(lines)

    @staticmethod
    def to_dict(state: SessionState) -> Dict[str, Any]:
        """Return structured dictionary for state serialization or API/Supervisor consumption."""
        return state.to_dict()
