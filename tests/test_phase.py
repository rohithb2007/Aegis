import pytest
from observer.events import AntigravityEvent, EventType
from supervisor.state import SessionState, CommandRecord, CommandStatus
from supervisor.phase import PhaseDetector, WorkflowPhase


def test_phase_detection_research():
    detector = PhaseDetector()
    state = SessionState(session_id="s1", started_at="T1", last_activity="T1")

    ev = AntigravityEvent(timestamp="T1", event_type=EventType.VIEW_FILE, file_path="main.py")
    phase, reason = detector.detect(ev, state)
    assert phase == WorkflowPhase.RESEARCH
    assert "inspection" in reason.lower()


def test_phase_detection_implementation():
    detector = PhaseDetector()
    state = SessionState(session_id="s1", started_at="T1", last_activity="T1")

    ev = AntigravityEvent(timestamp="T1", event_type=EventType.EDIT_FILE, file_path="main.py")
    phase, reason = detector.detect(ev, state)
    assert phase == WorkflowPhase.IMPLEMENTATION
    assert "edit" in reason.lower()


def test_phase_detection_verification():
    detector = PhaseDetector()
    state = SessionState(session_id="s1", started_at="T1", last_activity="T1")

    ev = AntigravityEvent(timestamp="T1", event_type=EventType.RUN_COMMAND, command="python -m pytest -v")
    phase, reason = detector.detect(ev, state)
    assert phase == WorkflowPhase.VERIFICATION
    assert "pytest" in reason.lower()


def test_phase_detection_debugging():
    detector = PhaseDetector()
    state = SessionState(session_id="s1", started_at="T1", last_activity="T1")
    state.commands.append(CommandRecord(timestamp="T1", command="pytest", status=CommandStatus.FAILURE))

    ev = AntigravityEvent(timestamp="T2", event_type=EventType.EDIT_FILE, file_path="fix.py")
    phase, reason = detector.detect(ev, state)
    assert phase == WorkflowPhase.DEBUGGING
    assert "debugging retry" in reason.lower()


def test_phase_detection_completion():
    detector = PhaseDetector()
    state = SessionState(session_id="s1", started_at="T1", last_activity="T1")

    ev = AntigravityEvent(timestamp="T1", event_type=EventType.TASK_COMPLETED, task_id="task-1")
    phase, reason = detector.detect(ev, state)
    assert phase == WorkflowPhase.COMPLETION
