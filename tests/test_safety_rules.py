import pytest
from safety.patterns import CommandParser
from safety.rules import SecurityRuleRegistry, RuleEngine
from safety.models import SafetyClassification, CapabilityType


def test_command_parser_single():
    parser = CommandParser()
    parsed = parser.parse("python -m pytest -v")
    assert parsed.executable == "pytest" or parsed.executable == "python"

    git_push = parser.parse("git push --force origin main")
    assert git_push.executable == "git"
    assert git_push.subcommand == "push"
    assert "--force" in git_push.flags


def test_command_parser_compound_split():
    parser = CommandParser()
    compound = parser.parse("git status && git push")
    assert compound.is_compound is True
    assert len(compound.sub_commands) == 2
    assert compound.sub_commands[0].subcommand == "status"
    assert compound.sub_commands[1].subcommand == "push"


def test_false_positive_prevention_rm_in_filename():
    parser = CommandParser()
    parsed = parser.parse("pytest -v tests/test_normalizer.py")
    assert parsed.executable == "pytest"
    assert parsed.executable != "rm"

    engine = RuleEngine()
    matched = engine.evaluate(parsed)
    rule_names = [r.name for r, _ in matched]
    assert "SafeReadCommands" in rule_names
    assert "FilesystemDeletion" not in rule_names
    assert "RecursiveDestructiveDeletion" not in rule_names


def test_safe_read_rules():
    engine = RuleEngine()
    parser = CommandParser()

    for cmd in ["git status", "git diff", "git log", "pytest -v", "npm test"]:
        p = parser.parse(cmd)
        matched = engine.evaluate(p)
        rule_names = [r.name for r, _ in matched]
        assert len(rule_names) > 0


def test_package_installation_rule():
    engine = RuleEngine()
    parser = CommandParser()

    p = parser.parse("pip install requests")
    matched = engine.evaluate(p)
    rule_names = [r.name for r, _ in matched]
    assert "PackageInstallation" in rule_names


def test_destructive_rules():
    engine = RuleEngine()
    parser = CommandParser()

    p_rm = parser.parse("rm -rf /")
    matched_rm = engine.evaluate(p_rm)
    rule_names_rm = [r.name for r, _ in matched_rm]
    assert "RecursiveDestructiveDeletion" in rule_names_rm or "CriticalSystemDestruction" in rule_names_rm

    p_drop = parser.parse("python -c \"DROP TABLE users;\"")
    matched_drop = engine.evaluate(p_drop)
    rule_names_drop = [r.name for r, _ in matched_drop]
    assert "CriticalSystemDestruction" in rule_names_drop


def test_obfuscation_rule():
    engine = RuleEngine()
    parser = CommandParser()

    p = parser.parse("powershell -EncodedCommand JABzAD0...")
    matched = engine.evaluate(p)
    rule_names = [r.name for r, _ in matched]
    assert "ObfuscatedExecution" in rule_names
