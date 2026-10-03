import os
from typing import Optional, List, Dict, Any
from supervisor.state import SessionState
from ai_supervisor.sanitizer import ContextSanitizer
from .models import WorkspaceBoundary, ProtectedContext


class ProtectedSession:
    """Manages workspace session context and boundary validation for Aegis V0.8."""

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        session_state: Optional[SessionState] = None,
    ):
        root = workspace_root or os.getcwd()
        self.boundary = WorkspaceBoundary(workspace_root=root)
        self.session_state = session_state
        self.sanitizer = ContextSanitizer()

    def get_context(self, cwd: Optional[str] = None) -> ProtectedContext:
        work_dir = cwd or os.getcwd()
        session_id = self.session_state.session_id if self.session_state else None
        task_id = self.session_state.active_task_id if self.session_state else None
        goal = self.session_state.current_goal if self.session_state else None
        phase = self.session_state.current_phase if self.session_state else None
        rec_files = self.session_state.inspected_files[-5:] if self.session_state else []
        rec_errs = [e.message for e in (self.session_state.errors[-5:] if self.session_state else [])]

        return ProtectedContext(
            workspace_root=self.boundary.workspace_root,
            cwd=work_dir,
            session_id=session_id,
            task_id=task_id,
            user_goal=goal,
            workflow_phase=phase,
            recent_files=rec_files,
            recent_errors=rec_errs,
        )

    def is_within_workspace(self, path: str) -> bool:
        return self.boundary.is_path_inside(path)
