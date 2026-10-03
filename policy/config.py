import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class PolicyMode(str, Enum):
    STRICT = "STRICT"
    BALANCED = "BALANCED"
    PERMISSIVE = "PERMISSIVE"


@dataclass
class PolicyConfig:
    mode: PolicyMode = PolicyMode.BALANCED

    @classmethod
    def from_env_or_dict(cls, config_dict: Optional[Dict[str, Any]] = None) -> "PolicyConfig":
        env_mode = os.getenv("AEGIS_POLICY_MODE")
        dict_mode = (config_dict or {}).get("mode") if config_dict else None
        mode_str = (env_mode or dict_mode or "BALANCED").upper()

        try:
            mode = PolicyMode(mode_str)
        except ValueError:
            mode = PolicyMode.BALANCED

        return cls(mode=mode)
