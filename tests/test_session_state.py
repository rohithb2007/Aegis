import pytest
from observer.events import AntigravityEvent, EventType
from supervisor.state import (
    SessionState, TaskState, CommandRecord, ErrorRecord,
    TaskStatus, CommandStatus, ErrorSeverity
)
from supervisor.session import SessionTracker


def test_session_state_initialization():
    tracker = SessionTracker(session_id="sess-001")
    assert tracker.state.session_id == "sess-001"
    assert tracker.state.current_phase == "UNKNOWN"
    assert len(tracker.state.inspected_files) == 0
    assert len(tracker.state.modified_files) == 0


def test_file_tracking():
    tracker = SessionTracker(session_id="sess-001")
    
    view_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.VIEW_FILE,
        file_path="src/app.py"
    )
    tracker.process_event(view_ev)
    assert "src/app.py" in tracker.state.inspected_files
    assert "src/app.py" not in tracker.state.modified_files

    edit_ev = AntigravityEvent(
        timestamp="2026-09-20T00:01:00Z",
        event_type=EventType.EDIT_FILE,
        file_path="src/app.py"
    )
    tracker.process_event(edit_ev)
    assert "src/app.py" in tracker.state.modified_files


def test_command_tracking_and_results():
    tracker = SessionTracker(session_id="sess-001")

    cmd_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.RUN_COMMAND,
        command="python -m pytest -v",
        task_id="task-10"
    )
    tracker.process_event(cmd_ev)

    assert len(tracker.state.commands) == 1
    assert tracker.state.commands[0].command == "python -m pytest -v"
    assert tracker.state.commands[0].status == CommandStatus.PENDING

    res_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:05Z",
        event_type=EventType.COMMAND_RESULT,
        command="python -m pytest -v",
        task_id="task-10",
        result_summary="22 passed"
    )
    tracker.process_event(res_ev)

    assert tracker.state.commands[0].status == CommandStatus.SUCCESS
    assert tracker.state.commands[0].output_summary == "22 passed"


def test_task_lifecycle_tracking():
    tracker = SessionTracker(session_id="sess-001")

    start_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.TASK_STARTED,
        task_id="task-100"
    )
    tracker.process_event(start_ev)
    assert tracker.state.active_task_id == "task-100"
    assert tracker.state.task_status == "ACTIVE"
    assert "task-100" in tracker.state.tasks

    comp_ev = AntigravityEvent(
        timestamp="2026-09-20T00:05:00Z",
        event_type=EventType.TASK_COMPLETED,
        task_id="task-100"
    )
    tracker.process_event(comp_ev)
    assert "task-100" in tracker.state.completed_tasks
    assert tracker.state.tasks["task-100"].status == TaskStatus.COMPLETED


def test_error_tracking():
    tracker = SessionTracker(session_id="sess-001")

    fail_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.TASK_FAILED,
        task_id="task-200",
        result_summary="Build failed with syntax error"
    )
    tracker.process_event(fail_ev)

    assert "task-200" in tracker.state.failed_tasks
    assert len(tracker.state.errors) == 1
    assert tracker.state.errors[0].severity == ErrorSeverity.HIGH


def test_bounded_history_trimming():
    state = SessionState(
        session_id="sess-001",
        started_at="2026-09-20T00:00:00Z",
        last_activity="2026-09-20T00:00:00Z",
        max_recent_events=5,
        max_command_history=5
    )

    for i in range(10):
        ev = AntigravityEvent(timestamp=f"T{i}", event_type=EventType.VIEW_FILE, file_path=f"file{i}.py")
        state.recent_events.append(ev)
        state.commands.append(CommandRecord(timestamp=f"T{i}", command=f"cmd_{i}"))

    state.trim_history()
    assert len(state.recent_events) == 5
    assert state.recent_events[0].file_path == "file5.py"
    assert len(state.commands) == 5
    assert state.commands[0].command == "cmd_5"
