import os
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AIProvider(ABC):
    """Abstract interface for AI supervisor providers."""

    @abstractmethod
    def analyze(self, sanitized_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send sanitized context to AI provider and return parsed JSON result dictionary."""
        pass


class MockProvider(AIProvider):
    """Deterministic, 100% network-free mock provider for test suites and offline execution."""

    def analyze(self, sanitized_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cmd = (sanitized_context.get("current_command") or "").lower()
        goal = (sanitized_context.get("user_goal") or "").lower()
        phase = (sanitized_context.get("workflow_phase") or "").upper()
        safety = sanitized_context.get("safety_assessment") or {}
        classif = safety.get("classification", "SAFE")

        # 1. Verification / Read commands aligned
        if any(kw in cmd for kw in ["pytest", "git status", "git diff", "git log", "git branch", "git show", "npm test", "get-childitem", "get-content", "get-item", "get-location", "get-process", "ls", "dir", "cat", "type", "whoami", "pwd"]):
            return {
                "verdict": "ALIGNED",
                "confidence": "HIGH",
                "alignment": "ALIGNED",
                "explanation": "Command directly aligns with active task and read-only/verification activity.",
                "concerns": [],
                "recommended_action": "NO_CONCERN"
            }

        # 2. Package install - questionable / needs review if context is uncertain
        if any(kw in cmd for kw in ["pip install", "npm install", "yarn add", "cargo add", "go get"]):
            return {
                "verdict": "QUESTIONABLE",
                "confidence": "MEDIUM",
                "alignment": "PARTIALLY_ALIGNED",
                "explanation": "Package installation modifies dependencies; context does not explicitly specify dependency requirement.",
                "concerns": ["External package download and dependency modification."],
                "recommended_action": "REVIEW"
            }

        # 3. High risk force push or destructive command - suspicious / human review
        if any(kw in cmd for kw in ["git push", "rm -rf", "reset --hard", "drop table", "drop database", "truncate", "remove-item -recurse"]) or ("git" in cmd and "push" in cmd and ("force" in cmd or "-f" in cmd)):
            return {
                "verdict": "NEEDS_HUMAN_REVIEW" if "push" in cmd else "SUSPICIOUS",
                "confidence": "HIGH",
                "alignment": "NOT_ALIGNED",
                "explanation": f"Command involves high-impact action ('{cmd[:40]}') not established as required by the current task.",
                "concerns": ["Potential remote state modification or destructive filesystem removal."],
                "recommended_action": "REVIEW" if "push" in cmd else "ESCALATE"
            }

        # Default fallback for mock
        return {
            "verdict": "ALIGNED" if classif in ["SAFE", "LOW_RISK"] else "NEEDS_HUMAN_REVIEW",
            "confidence": "MEDIUM",
            "alignment": "ALIGNED" if classif in ["SAFE", "LOW_RISK"] else "PARTIALLY_ALIGNED",
            "explanation": f"Evaluated command execution under phase {phase}.",
            "concerns": [],
            "recommended_action": "NO_CONCERN" if classif in ["SAFE", "LOW_RISK"] else "REVIEW"
        }


class OpenAIProvider(AIProvider):
    """OpenAI API-compatible provider using urllib (no extra dependencies required)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("AEGIS_AI_MODEL", "gpt-4o-mini")

    def analyze(self, sanitized_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        prompt_data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are the contextual security supervisor for an AI coding agent. Output valid JSON only."},
                {"role": "user", "content": json.dumps(sanitized_context, indent=2)}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(prompt_data).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception:
            return None


def get_provider_from_env() -> AIProvider:
    """Factory helper to return configured provider or fallback to MockProvider."""
    provider_name = os.environ.get("AEGIS_AI_PROVIDER", "mock").lower()
    if provider_name == "openai" and os.environ.get("OPENAI_API_KEY"):
        return OpenAIProvider()
    return MockProvider()
