"""
Aegis Supervisor Package — Session Understanding & Context Layer
"""

from .state import (
    SessionState, TaskState, CommandRecord, ErrorRecord,
    TaskStatus, CommandStatus, ErrorSeverity
)
from .phase import WorkflowPhase, PhaseDetector
from .context import GoalTracker, ContextSnapshot
from .session import SessionTracker

__all__ = [
    "SessionState",
    "TaskState",
    "CommandRecord",
    "ErrorRecord",
    "TaskStatus",
    "CommandStatus",
    "ErrorSeverity",
    "WorkflowPhase",
    "PhaseDetector",
    "GoalTracker",
    "ContextSnapshot",
    "SessionTracker",
]
