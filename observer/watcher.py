import os
import time
import glob
from typing import Optional, List, Callable
from .events import AntigravityEvent
from .parser import AntigravityParser


class SessionWatcher:
    """Monitors Antigravity directories and streams live events."""

    def __init__(self, base_dir: Optional[str] = None, poll_interval: float = 1.0):
        self.base_dir = base_dir or self.detect_antigravity_dir()
        self.poll_interval = poll_interval
        self.parser = AntigravityParser()
        self.active_session_id: Optional[str] = None
        self.processed_message_files: set = set()
        self.task_log_offsets: dict = {}
        self.callbacks: List[Callable[[AntigravityEvent], None]] = []

    @staticmethod
    def detect_antigravity_dir() -> str:
        """Locate the default Antigravity data directory for the current user."""
        user_home = os.path.expanduser("~")
        default_dir = os.path.join(user_home, ".gemini", "antigravity-ide")
        if os.path.exists(default_dir):
            return default_dir
        raise FileNotFoundError(f"Antigravity IDE directory not found at: {default_dir}")

    def add_callback(self, callback: Callable[[AntigravityEvent], None]):
        """Register a callback function to receive parsed events."""
        self.callbacks.append(callback)

    def _emit(self, event: AntigravityEvent):
        """Emit an event to all registered callbacks."""
        for cb in self.callbacks:
            try:
                cb(event)
            except Exception as e:
                print(f"[Aegis] Callback error: {e}")

    def discover_active_session(self) -> Optional[str]:
        """Find the most recently modified conversation session ID."""
        brain_dir = os.path.join(self.base_dir, "brain")
        if not os.path.exists(brain_dir):
            return None

        sessions = []
        for entry in os.listdir(brain_dir):
            path = os.path.join(brain_dir, entry)
            if os.path.isdir(path) and entry != "tempmediaStorage":
                mtime = os.path.getmtime(path)
                sessions.append((entry, mtime))

        if not sessions:
            return None

        # Sort by modification time descending
        sessions.sort(key=lambda x: x[1], reverse=True)
        return sessions[0][0]

    def poll_once(self) -> List[AntigravityEvent]:
        """Perform a single polling cycle over active session logs and databases."""
        new_events: List[AntigravityEvent] = []

        latest_session = self.discover_active_session()
        if not latest_session:
            return new_events

        if latest_session != self.active_session_id:
            self.active_session_id = latest_session
            print(f"[Aegis] Monitoring session: {self.active_session_id}")

        session_dir = os.path.join(self.base_dir, "brain", self.active_session_id)
        system_gen_dir = os.path.join(session_dir, ".system_generated")

        # 1. Scan message JSON files in .system_generated/messages
        messages_dir = os.path.join(system_gen_dir, "messages")
        if os.path.exists(messages_dir):
            json_files = glob.glob(os.path.join(messages_dir, "*.json"))
            for jf in json_files:
                if jf not in self.processed_message_files:
                    parsed = self.parser.parse_message_json(jf, self.active_session_id)
                    for ev in parsed:
                        new_events.append(ev)
                        self._emit(ev)
                    self.processed_message_files.add(jf)

        # 2. Scan task log files in .system_generated/tasks
        tasks_dir = os.path.join(system_gen_dir, "tasks")
        if os.path.exists(tasks_dir):
            log_files = glob.glob(os.path.join(tasks_dir, "*.log"))
            for lf in log_files:
                parsed = self.parser.parse_task_log(lf, self.active_session_id)
                for ev in parsed:
                    new_events.append(ev)
                    self._emit(ev)

        # 3. Query SQLite DB in conversations/<session-id>.db
        db_path = os.path.join(self.base_dir, "conversations", f"{self.active_session_id}.db")
        if os.path.exists(db_path):
            parsed = self.parser.parse_sqlite_db(db_path, self.active_session_id)
            for ev in parsed:
                new_events.append(ev)
                self._emit(ev)

        return new_events

    def start(self):
        """Start the continuous live monitoring loop."""
        print("[Aegis] Starting observer...")
        print(f"[Aegis] Antigravity directory detected: {self.base_dir}")

        initial_session = self.discover_active_session()
        if initial_session:
            self.active_session_id = initial_session
            print(f"[Aegis] Monitoring session: {self.active_session_id}")
        else:
            print("[Aegis] Waiting for active session...")

        try:
            while True:
                self.poll_once()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[Aegis] Observer stopped by user.")
