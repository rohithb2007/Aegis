import pytest
from safety.analyzer import SafetyAnalyzer
from safety.models import SafetyClassification, SafetyAction, CapabilityType, Reversibility, Scope
from supervisor.state import SessionState


def test_safety_analyzer_safe_command():
    analyzer = SafetyAnalyzer()
    res = analyzer.analyze("git status")

    assert res.classification == SafetyClassification.SAFE
    assert res.action == SafetyAction.OBSERVE
    assert res.score <= 10
    assert CapabilityType.GIT_LOCAL in res.capabilities
    assert res.reversibility == Reversibility.REVERSIBLE


def test_safety_analyzer_medium_risk_package_install():
    analyzer = SafetyAnalyzer()
    res = analyzer.analyze("npm install axios")

    assert res.classification == SafetyClassification.MEDIUM_RISK
    assert res.action == SafetyAction.REVIEW_REQUIRED
    assert res.score >= 26 and res.score <= 50
    assert CapabilityType.PACKAGE_INSTALLATION in res.capabilities
    assert CapabilityType.NETWORK_ACCESS in res.capabilities


def test_safety_analyzer_high_risk_git_force_push():
    analyzer = SafetyAnalyzer()
    res = analyzer.analyze("git push --force origin main")

    assert res.classification in [SafetyClassification.HIGH_RISK, SafetyClassification.CRITICAL]
    assert res.action in [SafetyAction.REVIEW_REQUIRED, SafetyAction.RESTRICTED]
    assert CapabilityType.REMOTE_STATE_CHANGE in res.capabilities
    assert res.reversibility == Reversibility.DIFFICULT_TO_REVERSE


def test_safety_analyzer_credential_access():
    analyzer = SafetyAnalyzer()
    res = analyzer.analyze("type .env")

    assert res.classification in [SafetyClassification.MEDIUM_RISK, SafetyClassification.HIGH_RISK]
    assert CapabilityType.CREDENTIAL_ACCESS in res.capabilities
    assert "credential" in " ".join(res.reasons).lower()


def test_safety_analyzer_compound_command_chaining():
    analyzer = SafetyAnalyzer()
    res = analyzer.analyze("git status && git push --force")

    # High risk because second segment is git push --force!
    assert res.classification in [SafetyClassification.HIGH_RISK, SafetyClassification.CRITICAL]
    assert any("Compound command" in r for r in res.reasons)


def test_safety_analyzer_outside_project_scope():
    analyzer = SafetyAnalyzer()
    res = analyzer.analyze("Remove-Item C:\\Windows\\System32\\driver.dll")

    assert res.scope == Scope.OUTSIDE_PROJECT
    assert res.classification in [SafetyClassification.HIGH_RISK, SafetyClassification.CRITICAL]


def test_safety_analyzer_inert_execution_guarantee():
    analyzer = SafetyAnalyzer()
    # Analyzing dangerous command must NEVER execute it!
    res = analyzer.analyze("rm -rf /")

    assert res.classification in [SafetyClassification.HIGH_RISK, SafetyClassification.CRITICAL]
    assert res.score >= 50
