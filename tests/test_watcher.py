import os
import json
import time
import pytest
from observer.watcher import SessionWatcher
from observer.events import EventType, AntigravityEvent


def test_session_watcher_discovery(tmp_path):
    base_dir = tmp_path / "antigravity-ide"
    brain_dir = base_dir / "brain"
    brain_dir.mkdir(parents=True)

    sess1 = brain_dir / "sess-111"
    sess1.mkdir()
    time.sleep(0.05)

    sess2 = brain_dir / "sess-222"
    sess2.mkdir()

    watcher = SessionWatcher(base_dir=str(base_dir))
    active = watcher.discover_active_session()
    assert active == "sess-222"


def test_session_watcher_polling(tmp_path):
    base_dir = tmp_path / "antigravity-ide"
    brain_dir = base_dir / "brain"
    sess_dir = brain_dir / "sess-abc"
    msg_dir = sess_dir / ".system_generated" / "messages"
    msg_dir.mkdir(parents=True)

    msg_file = msg_dir / "test_msg.json"
    data = {
        "id": "msg-999",
        "timestamp": "2026-09-20T02:00:00Z",
        "renderDetails": {"messageTitle": "Build project finished"},
        "content": "Build succeeded"
    }
    msg_file.write_text(json.dumps(data), encoding="utf-8")

    watcher = SessionWatcher(base_dir=str(base_dir))
    emitted_events = []
    watcher.add_callback(lambda ev: emitted_events.append(ev))

    events = watcher.poll_once()
    assert len(events) >= 1
    assert len(emitted_events) >= 1
    assert emitted_events[0].event_type == EventType.TASK_COMPLETED
