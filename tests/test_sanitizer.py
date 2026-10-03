import pytest
from ai_supervisor.sanitizer import ContextSanitizer
from supervisor.state import SessionState
from safety.models import SafetyAssessment, SafetyClassification, SafetyAction, CapabilityType, Reversibility, Scope


def test_secret_redaction_api_keys_and_passwords():
    sanitizer = ContextSanitizer()

    input_cmd = "python -c 'API_KEY=super-secret-value-12345; password=myPassword99; Bearer eyJhbGciOiJIUzI1Ni...'"
    redacted = sanitizer.redact_secrets(input_cmd)

    assert "super-secret-value-12345" not in redacted
    assert "myPassword99" not in redacted
    assert "[REDACTED]" in redacted
    assert "API_KEY=[REDACTED]" in redacted or "api_key" in redacted.lower()


def test_secret_redaction_sk_keys_and_github_tokens():
    sanitizer = ContextSanitizer()

    input_text = "Deploying with sk-proj-1234567890abcdef123456 and ghp_abcdefghijklmnopqrstuvwxyz1234"
    redacted = sanitizer.redact_secrets(input_text)

    assert "sk-proj-1234567890abcdef123456" not in redacted
    assert "ghp_abcdefghijklmnopqrstuvwxyz1234" not in redacted
    assert "sk-[REDACTED]" in redacted
    assert "ghp_[REDACTED]" in redacted


def test_context_sanitization_bounded_metadata():
    sanitizer = ContextSanitizer()
    state = SessionState(session_id="s1", started_at="T1", last_activity="T2", current_goal="Fix API_KEY=secret_123456 bug")
    state.add_inspected_file("src/auth.py")
    state.add_modified_file("src/auth.py")

    safety = SafetyAssessment(
        command="python main.py",
        classification=SafetyClassification.SAFE,
        action=SafetyAction.OBSERVE,
        score=0,
        capabilities=[CapabilityType.EXECUTE_PROCESS],
        reversibility=Reversibility.REVERSIBLE,
        scope=Scope.INSIDE_PROJECT
    )

    ctx = sanitizer.sanitize_context(state, safety, "python main.py")

    assert ctx["current_command"] == "python main.py"
    assert "secret_123456" not in ctx["user_goal"]
    assert "[REDACTED]" in ctx["user_goal"]
    assert "src/auth.py" in ctx["files_inspected"]
    # Source contents of src/auth.py are NOT included in context dictionary!
    assert "source_code" not in ctx
