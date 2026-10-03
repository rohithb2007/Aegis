import os
import tempfile
import pytest
from policy.audit import AuditLogger, AuditRecord


def test_audit_record_generation_and_serialization():
    logger = AuditLogger()
    record = logger.log(
        command="git status",
        v03_risk="SAFE",
        risk_score=0,
        capabilities=["READ_FILESYSTEM"],
        final_policy_decision="ALLOW",
        policy_reasons=["Routine safe action."],
        v04_verdict="ALIGNED",
        v05_route="NO_AI",
        approval_status="AUTO_ALLOWED"
    )

    assert record.record_id.startswith("aud-")
    assert record.command == "git status"
    assert record.v03_risk == "SAFE"
    assert record.final_policy_decision == "ALLOW"
    assert record.policy_version == "0.6.0"

    d = record.to_dict()
    assert d["record_id"] == record.record_id
    assert d["command"] == "git status"
    assert d["policy_version"] == "0.6.0"
    assert d["approval_status"] == "AUTO_ALLOWED"


def test_audit_secret_redaction():
    logger = AuditLogger()
    secret_cmd = "curl -H 'Authorization: Bearer sk-1234567890abcdef1234567' http://api.com?token=ghp_123456789012345678901234567890123456"
    record = logger.log(
        command=secret_cmd,
        v03_risk="HIGH_RISK",
        risk_score=80,
        capabilities=["NETWORK_ACCESS", "CREDENTIAL_ACCESS"],
        final_policy_decision="REVIEW",
        policy_reasons=["Command contains password=mysecretpassword123"],
        v04_verdict="SUSPICIOUS",
        v05_route="STRONG_AI"
    )

    assert "sk-1234567890abcdef1234567" not in record.command
    assert "ghp_123456789012345678901234567890123456" not in record.command
    assert "[REDACTED]" in record.command

    # Reason sanitization check
    assert "mysecretpassword123" not in record.policy_reasons[0]


def test_audit_logger_file_append():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        logger = AuditLogger(log_filepath=tmp_path)
        logger.log(
            command="ls -la",
            v03_risk="LOW_RISK",
            risk_score=15,
            capabilities=["READ_FILESYSTEM"],
            final_policy_decision="ALLOW",
            policy_reasons=["Safe read"]
        )

        with open(tmp_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            assert "ls -la" in lines[0]
            assert "0.6.0" in lines[0]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
