import pytest
from observer.events import EventType, AntigravityEvent


def test_antigravity_event_to_dict():
    event = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.RUN_COMMAND,
        command="python -m pytest -v",
        task_id="task-565",
        session_id="session-123",
        raw="raw content"
    )

    data = event.to_dict()
    assert data["event_type"] == "RUN_COMMAND"
    assert data["source"] == "antigravity"
    assert data["command"] == "python -m pytest -v"
    assert data["task_id"] == "task-565"
    assert data["session_id"] == "session-123"
    assert "file_path" not in data  # filtered out None values


def test_antigravity_event_console_formatting():
    view_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.VIEW_FILE,
        file_path="src/engine.py"
    )
    assert view_ev.to_console_str() == "[VIEW] src/engine.py"

    edit_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.EDIT_FILE,
        file_path="src/engine.py"
    )
    assert edit_ev.to_console_str() == "[EDIT] src/engine.py"

    cmd_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.RUN_COMMAND,
        command="python main.py"
    )
    assert cmd_ev.to_console_str() == "[COMMAND]\npython main.py"

    res_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.COMMAND_RESULT,
        result_summary="22 passed"
    )
    assert res_ev.to_console_str() == "[RESULT]\n22 passed"

    comp_ev = AntigravityEvent(
        timestamp="2026-09-20T00:00:00Z",
        event_type=EventType.TASK_COMPLETED,
        task_id="task-565"
    )
    assert comp_ev.to_console_str() == "[TASK COMPLETED] task-565"
