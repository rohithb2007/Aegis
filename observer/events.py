import json
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Optional, Any, Dict
from datetime import datetime


class EventType(str, Enum):
    VIEW_FILE = "VIEW_FILE"
    EDIT_FILE = "EDIT_FILE"
    LIST_DIRECTORY = "LIST_DIRECTORY"
    RUN_COMMAND = "RUN_COMMAND"
    TOOL_CALL = "TOOL_CALL"
    COMMAND_RESULT = "COMMAND_RESULT"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    AGENT_MESSAGE = "AGENT_MESSAGE"


@dataclass
class AntigravityEvent:
    timestamp: str
    event_type: EventType
    source: str = "antigravity"
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    file_path: Optional[str] = None
    command: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    result_summary: Optional[str] = None
    raw: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to standard dictionary representation."""
        res = {
            "timestamp": self.timestamp,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else str(self.event_type),
            "source": self.source,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "file_path": self.file_path,
            "command": self.command,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "result_summary": self.result_summary,
            "raw": self.raw,
        }
        # Filter out None values for clean representation
        return {k: v for k, v in res.items() if v is not None}

    def to_console_str(self) -> str:
        """Format event into user-friendly console string."""
        ev_type = self.event_type.value if isinstance(self.event_type, EventType) else str(self.event_type)
        
        if ev_type == EventType.VIEW_FILE.value:
            target = self.file_path or (self.tool_args.get("AbsolutePath") if self.tool_args else "unknown file")
            return f"[VIEW] {target}"
            
        elif ev_type == EventType.EDIT_FILE.value:
            target = self.file_path or (self.tool_args.get("TargetFile") if self.tool_args else "unknown file")
            return f"[EDIT] {target}"

        elif ev_type == EventType.LIST_DIRECTORY.value:
            target = self.file_path or (self.tool_args.get("DirectoryPath") if self.tool_args else "unknown directory")
            return f"[LIST] {target}"

        elif ev_type == EventType.RUN_COMMAND.value:
            cmd = self.command or (self.tool_args.get("CommandLine") if self.tool_args else "")
            return f"[COMMAND]\n{cmd}"

        elif ev_type == EventType.COMMAND_RESULT.value:
            res = self.result_summary or "Completed"
            return f"[RESULT]\n{res}"

        elif ev_type == EventType.TASK_STARTED.value:
            tid = self.task_id or "unknown"
            return f"[TASK STARTED] {tid}"

        elif ev_type == EventType.TASK_COMPLETED.value:
            tid = self.task_id or "unknown"
            return f"[TASK COMPLETED] {tid}"

        elif ev_type == EventType.TASK_FAILED.value:
            tid = self.task_id or "unknown"
            return f"[TASK FAILED] {tid}"

        elif ev_type == EventType.AGENT_MESSAGE.value:
            msg = self.result_summary or ""
            return f"[AGENT MESSAGE] {msg[:120]}..." if len(msg) > 120 else f"[AGENT MESSAGE] {msg}"

        else:
            name = self.tool_name or ev_type
            return f"[{name}] {self.result_summary or self.command or self.file_path or ''}".strip()
