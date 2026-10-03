import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any, Set
from observer.events import AntigravityEvent, EventType


class TaskStatus(str, Enum):
    RUNNING = "RUNNING"
    ACTIVE = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"



class CommandStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class ErrorSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class TaskState:
    task_id: str
    started_at: str
    last_activity: str
    completed_at: Optional[str] = None
    status: TaskStatus = TaskStatus.ACTIVE
    commands: List[str] = field(default_factory=list)
    files_inspected: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "completed_at": self.completed_at,
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "commands": self.commands,
            "files_inspected": self.files_inspected,
            "files_modified": self.files_modified,
            "errors": self.errors,
        }


@dataclass
class CommandRecord:
    timestamp: str
    command: str
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    exit_code: Optional[int] = None
    status: CommandStatus = CommandStatus.PENDING
    duration: Optional[float] = None
    source: str = "antigravity"
    output_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "command": self.command,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "exit_code": self.exit_code,
            "status": self.status.value if isinstance(self.status, CommandStatus) else str(self.status),
            "duration": self.duration,
            "source": self.source,
            "output_summary": self.output_summary,
        }


@dataclass
class ErrorRecord:
    timestamp: str
    message: str
    task_id: Optional[str] = None
    command: Optional[str] = None
    source: str = "antigravity"
    severity: ErrorSeverity = ErrorSeverity.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "message": self.message,
            "task_id": self.task_id,
            "command": self.command,
            "source": self.source,
            "severity": self.severity.value if isinstance(self.severity, ErrorSeverity) else str(self.severity),
        }


@dataclass
class SessionState:
    session_id: str
    started_at: str
    last_activity: str
    active_task_id: Optional[str] = None
    task_status: Optional[str] = None
    current_goal: Optional[str] = None
    current_phase: str = "UNKNOWN"
    phase_reason: Optional[str] = None
    inspected_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    commands: List[CommandRecord] = field(default_factory=list)
    errors: List[ErrorRecord] = field(default_factory=list)
    recent_messages: List[str] = field(default_factory=list)
    recent_events: List[AntigravityEvent] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    tasks: Dict[str, TaskState] = field(default_factory=dict)

    # Max limits for bounded in-memory history
    max_recent_events: int = 100
    max_recent_messages: int = 50
    max_command_history: int = 100
    max_error_history: int = 50

    def add_inspected_file(self, file_path: str):
        if file_path and file_path not in self.inspected_files:
            self.inspected_files.append(file_path)

    def add_modified_file(self, file_path: str):
        if file_path and file_path not in self.modified_files:
            self.modified_files.append(file_path)

    def trim_history(self):
        """Bound memory usage during long-running sessions."""
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events = self.recent_events[-self.max_recent_events:]
        if len(self.recent_messages) > self.max_recent_messages:
            self.recent_messages = self.recent_messages[-self.max_recent_messages:]
        if len(self.commands) > self.max_command_history:
            self.commands = self.commands[-self.max_command_history:]
        if len(self.errors) > self.max_error_history:
            self.errors = self.errors[-self.max_error_history:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "active_task_id": self.active_task_id,
            "task_status": self.task_status,
            "current_goal": self.current_goal,
            "current_phase": self.current_phase,
            "phase_reason": self.phase_reason,
            "inspected_files_count": len(self.inspected_files),
            "inspected_files": self.inspected_files,
            "modified_files_count": len(self.modified_files),
            "modified_files": self.modified_files,
            "total_commands": len(self.commands),
            "last_command": self.commands[-1].command if self.commands else None,
            "last_result": self.commands[-1].status.value if self.commands and self.commands[-1].status else None,
            "total_errors": len(self.errors),
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
        }
