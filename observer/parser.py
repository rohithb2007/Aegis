import os
import json
import re
import sqlite3
import hashlib
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timezone
from .events import EventType, AntigravityEvent


def normalize_path(path: str) -> str:
    """Normalize file paths for consistent display and deduplication across Windows and POSIX."""
    if not path:
        return ""
    # Convert backslashes to forward slashes
    clean = path.replace("\\", "/")
    # Remove leading file:/// prefix if present
    if clean.startswith("file:///"):
        clean = clean[8:]
    elif clean.startswith("file://"):
        clean = clean[7:]
    # Replace multiple consecutive forward slashes
    clean = re.sub(r"/+", "/", clean)
    return clean


class AntigravityParser:
    """Parses raw Antigravity logs, JSON messages, and database records into structured AntigravityEvent objects."""

    def __init__(self):
        self.seen_event_ids: Set[str] = set()

    def _generate_event_id(self, event_type: str, session_id: Optional[str], key: str) -> str:
        raw_key = f"{event_type}:{session_id or ''}:{key}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def parse_message_json(self, file_path: str, session_id: Optional[str] = None) -> List[AntigravityEvent]:
        """Parse an Antigravity message JSON file from .system_generated/messages/*.json."""
        events: List[AntigravityEvent] = []
        if not os.path.exists(file_path):
            return events

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    return events
                data = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError, IOError):
            # Incomplete or non-JSON write; safely ignore
            return events

        if not isinstance(data, dict):
            return events

        msg_id = data.get("id") or os.path.basename(file_path)
        timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
        content_str = data.get("content", "")
        sender = data.get("sender", "")
        render_details = data.get("renderDetails") or {}
        title = render_details.get("messageTitle", "")

        # Extract task ID if present in sender string (e.g., "session-id/task-565")
        task_id = None
        if "/task-" in sender:
            task_id = sender.split("/")[-1]
        elif "task-" in title:
            match = re.search(r"task-\d+", title)
            if match:
                task_id = match.group(0)

        source_meta = data.get("sourceMetadata") or {}
        tool_data = source_meta.get("tool") or {}
        tool_call = tool_data.get("toolCall") or {}
        tool_name = tool_call.get("name")
        args_json = tool_call.get("argumentsJson")
        tool_args = {}
        if args_json:
            try:
                tool_args = json.loads(args_json)
            except (json.JSONDecodeError, TypeError):
                tool_args = {}

        # 1. Check tool execution finish / command result
        if tool_name == "run_command":
            cmd = tool_args.get("CommandLine", "")
            event_id = self._generate_event_id("RUN_COMMAND_MSG", session_id, msg_id)
            if event_id not in self.seen_event_ids:
                self.seen_event_ids.add(event_id)
                events.append(AntigravityEvent(
                    timestamp=timestamp,
                    event_type=EventType.RUN_COMMAND,
                    session_id=session_id,
                    task_id=task_id,
                    command=cmd,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    raw=data
                ))

            # Extract result summary from content
            res_summary = self._extract_result_summary(content_str)
            res_event_id = self._generate_event_id("COMMAND_RESULT_MSG", session_id, msg_id)
            if res_event_id not in self.seen_event_ids:
                self.seen_event_ids.add(res_event_id)
                events.append(AntigravityEvent(
                    timestamp=timestamp,
                    event_type=EventType.COMMAND_RESULT,
                    session_id=session_id,
                    task_id=task_id,
                    command=cmd,
                    result_summary=res_summary,
                    raw=content_str[:500] if content_str else None
                ))

        # 2. Check task completion or failure from message title
        if title:
            if "finished" in title.lower() or "completed" in title.lower():
                comp_event_id = self._generate_event_id("TASK_COMPLETED", session_id, f"{msg_id}:{task_id}")
                if comp_event_id not in self.seen_event_ids:
                    self.seen_event_ids.add(comp_event_id)
                    events.append(AntigravityEvent(
                        timestamp=timestamp,
                        event_type=EventType.TASK_COMPLETED,
                        session_id=session_id,
                        task_id=task_id or title,
                        result_summary=title,
                        raw=data
                    ))
            elif "failed" in title.lower() or "canceled" in title.lower() or "error" in title.lower():
                fail_event_id = self._generate_event_id("TASK_FAILED", session_id, f"{msg_id}:{task_id}")
                if fail_event_id not in self.seen_event_ids:
                    self.seen_event_ids.add(fail_event_id)
                    events.append(AntigravityEvent(
                        timestamp=timestamp,
                        event_type=EventType.TASK_FAILED,
                        session_id=session_id,
                        task_id=task_id or title,
                        result_summary=title,
                        raw=data
                    ))

        return events

    def parse_task_log(self, file_path: str, session_id: Optional[str] = None) -> List[AntigravityEvent]:
        """Parse stdout log content from a task-*.log file."""
        events: List[AntigravityEvent] = []
        if not os.path.exists(file_path):
            return events

        filename = os.path.basename(file_path)
        task_id = filename.replace(".log", "")

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except IOError:
            return events

        if not content.strip():
            return events

        event_id = self._generate_event_id("TASK_LOG", session_id, f"{task_id}:{len(content)}")
        if event_id in self.seen_event_ids:
            return events
        self.seen_event_ids.add(event_id)

        summary = self._extract_result_summary(content)
        timestamp = datetime.now(timezone.utc).isoformat()

        events.append(AntigravityEvent(
            timestamp=timestamp,
            event_type=EventType.COMMAND_RESULT,
            session_id=session_id,
            task_id=task_id,
            result_summary=summary,
            raw=content[:1000]
        ))
        return events

    def parse_sqlite_db(self, db_path: str, session_id: Optional[str] = None) -> List[AntigravityEvent]:
        """Query steps table in conversations/<session-id>.db in read-only mode."""
        events: List[AntigravityEvent] = []
        if not os.path.exists(db_path):
            return events

        uri_path = f"file:{os.path.abspath(db_path)}?mode=ro"
        try:
            conn = sqlite3.connect(uri_path, uri=True)
            cursor = conn.cursor()
            rows = cursor.execute(
                "SELECT idx, step_type, status, step_payload FROM steps WHERE step_payload IS NOT NULL ORDER BY idx ASC"
            ).fetchall()
            conn.close()
        except sqlite3.Error:
            return events

        timestamp = datetime.now(timezone.utc).isoformat()

        for idx, step_type, status, payload in rows:
            if not payload:
                continue

            event_id = self._generate_event_id("DB_STEP", session_id, str(idx))
            if event_id in self.seen_event_ids:
                continue

            # Decode payload text using latin-1 / utf-8 string extraction
            try:
                payload_str = payload.decode("utf-8", errors="replace")
            except Exception:
                payload_str = str(payload)

            parsed_events = self._parse_payload_strings(idx, payload_str, timestamp, session_id)
            if parsed_events:
                self.seen_event_ids.add(event_id)
                events.extend(parsed_events)

        return events

    def _parse_payload_strings(self, idx: int, payload_str: str, timestamp: str, session_id: Optional[str]) -> List[AntigravityEvent]:
        """Extract tool calls and actions from binary protobuf string representations."""
        events: List[AntigravityEvent] = []

        # 1. Check for view_file
        if "view_file" in payload_str:
            match = re.search(r'["\']AbsolutePath["\']\s*:\s*["\']([^"\']+)["\']', payload_str)
            path = normalize_path(match.group(1)) if match else None
            events.append(AntigravityEvent(
                timestamp=timestamp,
                event_type=EventType.VIEW_FILE,
                session_id=session_id,
                file_path=path,
                tool_name="view_file",
                raw=f"Step {idx}"
            ))

        # 2. Check for file edit tools (replace_file_content, write_to_file, multi_replace_file_content)
        elif any(tool in payload_str for tool in ["replace_file_content", "write_to_file", "multi_replace_file_content"]):
            match = re.search(r'["\']TargetFile["\']\s*:\s*["\']([^"\']+)["\']', payload_str)
            path = normalize_path(match.group(1)) if match else None
            tool_name = "replace_file_content" if "replace_file_content" in payload_str else ("write_to_file" if "write_to_file" in payload_str else "multi_replace_file_content")
            events.append(AntigravityEvent(
                timestamp=timestamp,
                event_type=EventType.EDIT_FILE,
                session_id=session_id,
                file_path=path,
                tool_name=tool_name,
                raw=f"Step {idx}"
            ))

        # 3. Check for list_dir
        elif "list_dir" in payload_str:
            match = re.search(r'["\']DirectoryPath["\']\s*:\s*["\']([^"\']+)["\']', payload_str)
            path = normalize_path(match.group(1)) if match else None
            events.append(AntigravityEvent(
                timestamp=timestamp,
                event_type=EventType.LIST_DIRECTORY,
                session_id=session_id,
                file_path=path,
                tool_name="list_dir",
                raw=f"Step {idx}"
            ))

        # 4. Check for run_command
        elif "run_command" in payload_str:
            match = re.search(r'["\']CommandLine["\']\s*:\s*["\']([^"\']+)["\']', payload_str)
            cmd = match.group(1) if match else None
            events.append(AntigravityEvent(
                timestamp=timestamp,
                event_type=EventType.RUN_COMMAND,
                session_id=session_id,
                command=cmd,
                tool_name="run_command",
                raw=f"Step {idx}"
            ))

        return events

    def _extract_result_summary(self, content: str) -> str:
        """Extract key status lines from test output or terminal logs."""
        if not content:
            return ""

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return ""

        # Search for pytest summaries like "22 passed", "1 failed", etc.
        for line in reversed(lines):
            if any(kw in line for kw in ["passed", "failed", "warning", "error", "Build succeeded", "COMPLETED", "Finished"]):
                return line.strip(" ==")

        # Fallback to last non-empty line
        return lines[-1][:120]
