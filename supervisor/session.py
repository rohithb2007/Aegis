from typing import Optional, Dict, Any
from datetime import datetime, timezone
from observer.events import AntigravityEvent, EventType
from .state import (
    SessionState, TaskState, CommandRecord, ErrorRecord,
    TaskStatus, CommandStatus, ErrorSeverity
)
from .phase import PhaseDetector, WorkflowPhase
from .context import GoalTracker


class SessionTracker:
    """Consumes normalized AntigravityEvent streams and maintains live SessionState memory."""

    def __init__(self, session_id: Optional[str] = None):
        now_iso = datetime.now(timezone.utc).isoformat()
        self.state = SessionState(
            session_id=session_id or "unknown",
            started_at=now_iso,
            last_activity=now_iso
        )
        self.phase_detector = PhaseDetector()
        self.goal_tracker = GoalTracker()

    def process_event(self, event: AntigravityEvent) -> SessionState:
        """Process a single event through the SessionTracker pipeline and update state."""
        # Update session ID if necessary
        if event.session_id and self.state.session_id != event.session_id and self.state.session_id == "unknown":
            self.state.session_id = event.session_id

        # Update last activity
        self.state.last_activity = event.timestamp or datetime.now(timezone.utc).isoformat()

        # Track active task ID if event carries task_id
        if event.task_id:
            self.state.active_task_id = event.task_id
            if event.task_id not in self.state.tasks:
                self.state.tasks[event.task_id] = TaskState(
                    task_id=event.task_id,
                    started_at=event.timestamp or self.state.last_activity,
                    last_activity=self.state.last_activity,
                    status=TaskStatus.ACTIVE
                )
            else:
                self.state.tasks[event.task_id].last_activity = self.state.last_activity

        active_task = self.state.tasks.get(self.state.active_task_id) if self.state.active_task_id else None

        ev_type = event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)

        # 1. File Inspections
        if ev_type == EventType.VIEW_FILE.value:
            path = event.file_path or (event.tool_args.get("AbsolutePath") if event.tool_args else None)
            if path:
                self.state.add_inspected_file(path)
                if active_task and path not in active_task.files_inspected:
                    active_task.files_inspected.append(path)

        elif ev_type == EventType.LIST_DIRECTORY.value:
            path = event.file_path or (event.tool_args.get("DirectoryPath") if event.tool_args else None)
            if path:
                self.state.add_inspected_file(path)
                if active_task and path not in active_task.files_inspected:
                    active_task.files_inspected.append(path)

        # 2. File Modifications
        elif ev_type == EventType.EDIT_FILE.value:
            path = event.file_path or (event.tool_args.get("TargetFile") if event.tool_args else None)
            if path:
                self.state.add_modified_file(path)
                if active_task and path not in active_task.files_modified:
                    active_task.files_modified.append(path)

        # 3. Commands
        elif ev_type == EventType.RUN_COMMAND.value:
            cmd = event.command or (event.tool_args.get("CommandLine") if event.tool_args else None)
            if cmd:
                rec = CommandRecord(
                    timestamp=event.timestamp or self.state.last_activity,
                    command=cmd,
                    task_id=event.task_id or self.state.active_task_id,
                    session_id=self.state.session_id,
                    status=CommandStatus.PENDING
                )
                self.state.commands.append(rec)
                if active_task and cmd not in active_task.commands:
                    active_task.commands.append(cmd)

        elif ev_type == EventType.COMMAND_RESULT.value:
            res_summary = event.result_summary or ""
            is_fail = any(kw in res_summary.lower() for kw in ["failed", "error", "exception"])
            status = CommandStatus.FAILURE if is_fail else CommandStatus.SUCCESS

            if self.state.commands:
                # Update last matching command
                last_cmd = self.state.commands[-1]
                last_cmd.status = status
                last_cmd.output_summary = res_summary
            else:
                # Create command record if standalone result arrived
                self.state.commands.append(CommandRecord(
                    timestamp=event.timestamp or self.state.last_activity,
                    command=event.command or "command",
                    task_id=event.task_id or self.state.active_task_id,
                    session_id=self.state.session_id,
                    status=status,
                    output_summary=res_summary
                ))

            if is_fail:
                err_rec = ErrorRecord(
                    timestamp=event.timestamp or self.state.last_activity,
                    message=f"Command execution error: {res_summary[:120]}",
                    task_id=event.task_id or self.state.active_task_id,
                    command=event.command,
                    severity=ErrorSeverity.MEDIUM
                )
                self.state.errors.append(err_rec)
                if active_task:
                    active_task.errors.append(res_summary)

        # 4. Task Lifecycle
        elif ev_type == EventType.TASK_STARTED.value:
            tid = event.task_id or "unknown"
            self.state.active_task_id = tid
            self.state.task_status = "ACTIVE"
            self.state.tasks[tid] = TaskState(
                task_id=tid,
                started_at=event.timestamp or self.state.last_activity,
                last_activity=self.state.last_activity,
                status=TaskStatus.ACTIVE
            )

        elif ev_type == EventType.TASK_COMPLETED.value:
            tid = event.task_id or self.state.active_task_id or "unknown"
            self.state.task_status = "COMPLETED"
            if tid not in self.state.completed_tasks:
                self.state.completed_tasks.append(tid)
            if tid in self.state.tasks:
                self.state.tasks[tid].status = TaskStatus.COMPLETED
                self.state.tasks[tid].completed_at = event.timestamp or self.state.last_activity

        elif ev_type == EventType.TASK_FAILED.value:
            tid = event.task_id or self.state.active_task_id or "unknown"
            self.state.task_status = "FAILED"
            if tid not in self.state.failed_tasks:
                self.state.failed_tasks.append(tid)
            if tid in self.state.tasks:
                self.state.tasks[tid].status = TaskStatus.FAILED
                self.state.tasks[tid].completed_at = event.timestamp or self.state.last_activity
            err_rec = ErrorRecord(
                timestamp=event.timestamp or self.state.last_activity,
                message=f"Task failure: {event.result_summary or tid}",
                task_id=tid,
                severity=ErrorSeverity.HIGH
            )
            self.state.errors.append(err_rec)

        # 5. Agent Messages & Goals
        elif ev_type == EventType.AGENT_MESSAGE.value:
            if event.result_summary:
                self.state.recent_messages.append(event.result_summary)

        # Goal Extraction
        new_goal = self.goal_tracker.extract_goal(event, self.state.current_goal)
        if new_goal:
            self.state.current_goal = new_goal

        # Workflow Phase Detection
        phase, reason = self.phase_detector.detect(event, self.state)
        self.state.current_phase = phase.value
        self.state.phase_reason = reason

        # Store recent event & trim history
        self.state.recent_events.append(event)
        self.state.trim_history()

        return self.state
