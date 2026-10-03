import pytest
import json
from ai_supervisor.prompt import PromptBuilder


def test_prompt_builder():
    builder = PromptBuilder()
    sanitizer_ctx = {
        "current_command": "python -m pytest -v",
        "user_goal": "Fix failing parser tests",
        "workflow_phase": "VERIFICATION",
        "safety_assessment": {"classification": "SAFE", "score": 0},
        "files_inspected": ["parser.py"],
        "files_modified": ["parser.py"]
    }

    prompt_str = builder.build_prompt(sanitizer_ctx)
    assert "contextual security supervisor" in prompt_str
    assert "python -m pytest -v" in prompt_str
    assert "Fix failing parser tests" in prompt_str

    parsed_json = json.loads(prompt_str)
    assert "system_instruction" in parsed_json
    assert "deterministic_facts" in parsed_json
    assert "requested_json_output_schema" in parsed_json
