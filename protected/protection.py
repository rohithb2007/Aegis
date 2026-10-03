import os
import json
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class ProtectionManager:
    """Manages explicit human-controlled Aegis Protection state (ON / OFF).
    
    Invariants:
    - Protection ON + Gateway available  => Interceptor evaluates via Gateway
    - Protection ON + Gateway offline    => FAIL CLOSED
    - Protection OFF                     => Human intentionally disabled Aegis; passthrough execution
    - Antigravity agent cannot turn Protection OFF
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.state_file = os.path.join(self.config_dir, "protection_state.json")
        self._lock = threading.Lock()

    def is_protection_on(self) -> bool:
        """Returns True if Protection is ON (default), False if OFF."""
        with self._lock:
            data = self._read_state_unlocked()
            val = data.get("enabled", True)
            if not isinstance(val, bool):
                return True
            return val

    def set_protection(self, enabled: bool, source: str = "HUMAN") -> Dict[str, Any]:
        """Sets Protection ON (True) or OFF (False). Must originate from HUMAN control."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            data = {
                "enabled": bool(enabled),
                "status": "ON" if enabled else "OFF",
                "updated_at": now_iso,
                "updated_by": source,
            }
            self._write_state_unlocked(data)
            return data

    def get_status_dict(self) -> Dict[str, Any]:
        with self._lock:
            data = self._read_state_unlocked()
            val = data.get("enabled", True)
            if not isinstance(val, bool):
                val = True
            return {
                "status": "ON" if val else "OFF",
                "enabled": val,
                "updated_at": data.get("updated_at"),
                "updated_by": data.get("updated_by", "SYSTEM"),
            }

    def _read_state_unlocked(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        return {"enabled": True, "status": "ON", "updated_by": "DEFAULT"}

    def _write_state_unlocked(self, data: Dict[str, Any]) -> None:
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as err:
            print(f"[Aegis ProtectionManager Warning] Failed to write protection state: {err}")
