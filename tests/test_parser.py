import os
import json
import sqlite3
import pytest
from observer.parser import AntigravityParser, normalize_path
from observer.events import EventType


def test_path_normalization():
    win_path = r"C:\Users\username\Projects\Aegis\main.py"
    norm = normalize_path(win_path)
    assert norm == "C:/Users/username/Projects/Aegis/main.py"

    uri_path = "file:///C:/Users/username/Projects/Aegis/main.py"
    assert normalize_path(uri_path) == "C:/Users/username/Projects/Aegis/main.py"


def test_parse_message_json_run_command(tmp_path):
    msg_file = tmp_path / "msg1.json"
    data = {
        "id": "msg-101",
        "recipient": "sess-1",
        "sender": "sess-1/task-565",
        "timestamp": "2026-09-20T01:00:00Z",
        "renderDetails": {"messageTitle": "Run pytest suite finished"},
        "content": "22 passed in 10.5s\nUnicode test:  Malayalam - പരീക്ഷണം Passed",
        "sourceMetadata": {
            "tool": {
                "conversationId": "sess-1",
                "stepIndex": 565,
                "toolCall": {
                    "id": "call_12345",
                    "name": "run_command",
                    "argumentsJson": json.dumps({
                        "CommandLine": "python -m pytest -v",
                        "Cwd": r"C:\Projects\Aegis"
                    })
                }
            }
        }
    }
    msg_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    parser = AntigravityParser()
    events = parser.parse_message_json(str(msg_file), session_id="sess-1")

    assert len(events) == 3
    event_types = [e.event_type for e in events]
    assert EventType.RUN_COMMAND in event_types
    assert EventType.COMMAND_RESULT in event_types
    assert EventType.TASK_COMPLETED in event_types

    cmd_event = [e for e in events if e.event_type == EventType.RUN_COMMAND][0]
    assert cmd_event.command == "python -m pytest -v"
    assert cmd_event.task_id == "task-565"

    comp_event = [e for e in events if e.event_type == EventType.TASK_COMPLETED][0]
    assert comp_event.task_id == "task-565"


def test_duplicate_event_prevention(tmp_path):
    msg_file = tmp_path / "msg1.json"
    data = {
        "id": "msg-101",
        "timestamp": "2026-09-20T01:00:00Z",
        "renderDetails": {"messageTitle": "Task finished"},
        "content": "Completed successfully"
    }
    msg_file.write_text(json.dumps(data), encoding="utf-8")

    parser = AntigravityParser()
    events_first = parser.parse_message_json(str(msg_file), session_id="sess-1")
    events_second = parser.parse_message_json(str(msg_file), session_id="sess-1")

    assert len(events_first) == 1
    assert len(events_second) == 0  # Deduplicated!


def test_partial_incomplete_log_writes(tmp_path):
    msg_file = tmp_path / "corrupted.json"
    msg_file.write_text("{\"id\": \"msg-101\", \"content\": ", encoding="utf-8")

    parser = AntigravityParser()
    events = parser.parse_message_json(str(msg_file), session_id="sess-1")
    assert events == []  # Handled safely without exception


def test_missing_invalid_log_files():
    parser = AntigravityParser()
    assert parser.parse_message_json("non_existent_file.json") == []
    assert parser.parse_task_log("non_existent_task.log") == []
    assert parser.parse_sqlite_db("non_existent.db") == []


def test_parse_task_log(tmp_path):
    log_file = tmp_path / "task-565.log"
    log_file.write_text("============================= test session starts =============================\n22 passed in 5.00s", encoding="utf-8")

    parser = AntigravityParser()
    events = parser.parse_task_log(str(log_file), session_id="sess-1")

    assert len(events) == 1
    assert events[0].event_type == EventType.COMMAND_RESULT
    assert events[0].task_id == "task-565"
    assert "22 passed" in events[0].result_summary


def test_parse_sqlite_db_tools(tmp_path):
    db_path = tmp_path / "test_session.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE steps (idx INT PRIMARY KEY, step_type INT, status INT, step_payload BLOB)")
    
    payload_view = '{"AbsolutePath": "C:\\\\Projects\\\\Aegis\\\\app.py", "toolAction": "Viewing file"}'.encode("utf-8")
    payload_edit = '{"TargetFile": "C:\\\\Projects\\\\Aegis\\\\app.py", "toolAction": "Replacing file"}'.encode("utf-8")
    payload_list = '{"DirectoryPath": "C:\\\\Projects\\\\Aegis", "toolAction": "Listing directory"}'.encode("utf-8")

    conn.execute("INSERT INTO steps VALUES (1, 15, 3, ?)", (("view_file " + payload_view.decode("utf-8")).encode("utf-8"),))
    conn.execute("INSERT INTO steps VALUES (2, 15, 3, ?)", (("replace_file_content " + payload_edit.decode("utf-8")).encode("utf-8"),))
    conn.execute("INSERT INTO steps VALUES (3, 15, 3, ?)", (("list_dir " + payload_list.decode("utf-8")).encode("utf-8"),))
    conn.commit()
    conn.close()

    parser = AntigravityParser()
    events = parser.parse_sqlite_db(str(db_path), session_id="test_session")

    assert len(events) == 3
    types = [e.event_type for e in events]
    assert EventType.VIEW_FILE in types
    assert EventType.EDIT_FILE in types
    assert EventType.LIST_DIRECTORY in types
