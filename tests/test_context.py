import pytest
from observer.events import AntigravityEvent, EventType
from supervisor.state import SessionState, CommandRecord, CommandStatus
from supervisor.context import GoalTracker, ContextSnapshot
from supervisor.session import SessionTracker


def test_goal_extraction():
    tracker = GoalTracker()
    ev = AntigravityEvent(
        timestamp="T1",
        event_type=EventType.AGENT_MESSAGE,
        result_summary="Goal: Implement user login authentication flow"
    )

    goal = tracker.extract_goal(ev)
    assert goal is not None
    assert "user login authentication flow" in goal.lower()


def test_goal_extraction_unknown_fallback():
    tracker = GoalTracker()
    ev = AntigravityEvent(
        timestamp="T1",
        event_type=EventType.VIEW_FILE,
        file_path="src/main.py"
    )

    goal = tracker.extract_goal(ev)
    assert goal is None


def test_context_snapshot_rendering():
    tracker = SessionTracker(session_id="session-999")
    tracker.state.current_goal = "Fix duplicate detection engine"
    tracker.state.current_phase = "VERIFICATION"
    tracker.state.phase_reason = "pytest command detected"

    ev1 = AntigravityEvent(timestamp="T1", event_type=EventType.VIEW_FILE, file_path="app.py")
    ev2 = AntigravityEvent(timestamp="T2", event_type=EventType.EDIT_FILE, file_path="app.py")
    ev3 = AntigravityEvent(timestamp="T3", event_type=EventType.RUN_COMMAND, command="python -m pytest -v")

    tracker.process_event(ev1)
    tracker.process_event(ev2)
    tracker.process_event(ev3)

    snapshot_text = ContextSnapshot.render_console(tracker.state)
    assert "AEGIS" in snapshot_text
    assert "Session: session-..." in snapshot_text
    assert "Fix duplicate detection engine" in snapshot_text
    assert "VERIFICATION" in snapshot_text
    assert "Verification command detected" in snapshot_text
    assert "Inspected: 1" in snapshot_text
    assert "Modified:  1" in snapshot_text

    dict_repr = ContextSnapshot.to_dict(tracker.state)
    assert dict_repr["session_id"] == "session-999"
    assert dict_repr["current_phase"] == "VERIFICATION"
    assert dict_repr["inspected_files_count"] == 1
    assert dict_repr["modified_files_count"] == 1
