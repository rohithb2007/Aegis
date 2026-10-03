import re
from typing import Dict, Any, List, Optional
from supervisor.state import SessionState
from safety.models import SafetyAssessment


class ContextSanitizer:
    """Deterministic context sanitizer and secret redactor for privacy preservation."""

    # Regex patterns for secret values, keys, and tokens
    SECRET_PATTERNS = [
        # Key-Value assignments: API_KEY=..., secret=..., password=...
        (r'(?i)(api[_-]?key|secret|password|passwd|token|auth[_-]?token|bearer|aws[_-]?access[_-]?key[_-]?id|aws[_-]?secret[_-]?access[_-]?key|github[_-]?token|private[_-]?key)\s*[:=]\s*["\']?([^"\'\s;]{4,})["\']?', r'\1=[REDACTED]'),
        # Bearer tokens in headers
        (r'(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}', r'Bearer [REDACTED]'),
        # OpenAI style keys (sk-...)
        (r'sk-[a-zA-Z0-9_\-]{15,}', r'sk-[REDACTED]'),
        # GitHub Personal Access Tokens (ghp_...)
        (r'ghp_[a-zA-Z0-9]{20,}', r'ghp_[REDACTED]'),
        # Generic PEM Private keys
        (r'-----BEGIN\s+([A-Z\s]+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+([A-Z\s]+)?PRIVATE\s+KEY-----', r'[REDACTED PRIVATE KEY]'),
    ]

    def redact_secrets(self, text: str) -> str:
        """Replace credential patterns in a string with [REDACTED]."""
        if not text:
            return ""
        sanitized = text
        for pat, repl in self.SECRET_PATTERNS:
            sanitized = re.sub(pat, repl, sanitized)
        return sanitized

    def sanitize_context(
        self,
        session_state: Optional[SessionState],
        safety_assessment: Optional[SafetyAssessment],
        current_command: str,
        max_files: int = 10,
        max_commands: int = 5,
        max_messages: int = 5
    ) -> Dict[str, Any]:
        """Build a bounded, secret-redacted metadata context payload for AI analysis."""
        clean_cmd = self.redact_secrets(current_command or "")

        goal = "Unknown"
        phase = "UNKNOWN"
        active_task = "None"
        inspected_files: List[str] = []
        modified_files: List[str] = []
        recent_commands: List[Dict[str, Any]] = []
        recent_messages: List[str] = []
        recent_errors: List[str] = []

        if session_state:
            goal = self.redact_secrets(session_state.current_goal or "Unknown")
            phase = session_state.current_phase or "UNKNOWN"
            active_task = session_state.active_task_id or "None"

            # Bound files (metadata only, no source contents)
            inspected_files = [self.redact_secrets(f) for f in session_state.inspected_files[-max_files:]]
            modified_files = [self.redact_secrets(f) for f in session_state.modified_files[-max_files:]]

            # Bound commands
            for rec in session_state.commands[-max_commands:]:
                recent_commands.append({
                    "command": self.redact_secrets(rec.command),
                    "status": rec.status.value if hasattr(rec.status, "value") else str(rec.status),
                    "output_summary": self.redact_secrets((rec.output_summary or "")[:200])
                })

            # Bound messages & errors
            recent_messages = [self.redact_secrets(m[:200]) for m in session_state.recent_messages[-max_messages:]]
            recent_errors = [self.redact_secrets(e.message[:200]) for e in session_state.errors[-5:]]

        # Bounded Safety Assessment
        safety_dict = {}
        if safety_assessment:
            safety_dict = {
                "classification": safety_assessment.classification.value if hasattr(safety_assessment.classification, "value") else str(safety_assessment.classification),
                "score": safety_assessment.score,
                "capabilities": [c.value if hasattr(c, "value") else str(c) for c in safety_assessment.capabilities],
                "reversibility": safety_assessment.reversibility.value if hasattr(safety_assessment.reversibility, "value") else str(safety_assessment.reversibility),
                "reasons": [self.redact_secrets(r) for r in safety_assessment.reasons]
            }

        return {
            "current_command": clean_cmd,
            "user_goal": goal,
            "active_task": active_task,
            "workflow_phase": phase,
            "files_inspected": inspected_files,
            "files_modified": modified_files,
            "recent_commands": recent_commands,
            "recent_messages": recent_messages,
            "recent_errors": recent_errors,
            "safety_assessment": safety_dict
        }
