import re
from dataclasses import dataclass, field
from typing import List, Callable, Optional, Tuple
from .models import CapabilityType, SafetyClassification, Reversibility
from .patterns import ParsedCommand


@dataclass
class Rule:
    name: str
    description: str
    capabilities: List[CapabilityType]
    score_delta: int
    severity: SafetyClassification
    reversibility: Reversibility
    explanation: str
    matcher: Callable[[ParsedCommand], bool]


class SecurityRuleRegistry:
    """Registry of composable deterministic security rules."""

    def __init__(self):
        self.rules: List[Rule] = []
        self._register_default_rules()

    def _register_default_rules(self):
        # 1. SAFE READ-ONLY COMMANDS
        self.rules.append(Rule(
            name="SafeReadCommands",
            description="Safe read-only inspection commands",
            capabilities=[CapabilityType.READ_FILESYSTEM],
            score_delta=0,
            severity=SafetyClassification.SAFE,
            reversibility=Reversibility.REVERSIBLE,
            explanation="Read-only diagnostic command with no filesystem or network mutation.",
            matcher=lambda cmd: (
                cmd.executable in [
                    "ls", "dir", "pwd", "whoami", "echo", "type", "cat",
                    "get-childitem", "get-content", "get-item", "get-location",
                    "get-process", "get-service", "select-string", "head", "tail", "grep", "findstr", "wc"
                ] and not any(f in (cmd.flags + cmd.args) for f in [">", ">>", "out-file", "set-content"])
            ) or (
                cmd.executable == "python" and any("pytest" in arg for arg in (cmd.args + cmd.flags))
            ) or (
                cmd.executable == "pytest"
            ) or (
                cmd.executable == "npm" and cmd.subcommand in ["test", "run"] and (not cmd.args or any(a in ["test", "build", "check"] for a in cmd.args))
            ) or (
                cmd.executable == "cargo" and cmd.subcommand in ["test", "check"]
            ) or (
                cmd.executable == "go" and cmd.subcommand == "test"
            )
        ))

        # 2. GIT LOCAL READ OPERATIONS
        self.rules.append(Rule(
            name="GitLocalRead",
            description="Git local read-only repository inspection",
            capabilities=[CapabilityType.GIT_LOCAL, CapabilityType.READ_FILESYSTEM],
            score_delta=0,
            severity=SafetyClassification.SAFE,
            reversibility=Reversibility.REVERSIBLE,
            explanation="Read-only Git operation (status/diff/log/branch).",
            matcher=lambda cmd: cmd.executable == "git" and cmd.subcommand in ["status", "diff", "log", "branch", "show"]
        ))

        # 3. GIT LOCAL MUTATION
        self.rules.append(Rule(
            name="GitLocalMutation",
            description="Git local repository mutation",
            capabilities=[CapabilityType.GIT_LOCAL, CapabilityType.WRITE_FILESYSTEM],
            score_delta=10,
            severity=SafetyClassification.LOW_RISK,
            reversibility=Reversibility.PARTIALLY_REVERSIBLE,
            explanation="Local Git state mutation (add/commit/stash).",
            matcher=lambda cmd: cmd.executable == "git" and cmd.subcommand in ["add", "commit", "stash", "checkout", "switch"] and not any("force" in f for f in cmd.flags)
        ))

        # 4. GIT REMOTE READ
        self.rules.append(Rule(
            name="GitRemoteRead",
            description="Git remote read operation",
            capabilities=[CapabilityType.GIT_REMOTE, CapabilityType.NETWORK_ACCESS],
            score_delta=15,
            severity=SafetyClassification.LOW_RISK,
            reversibility=Reversibility.REVERSIBLE,
            explanation="Fetches/pulls data from a remote Git repository over the network.",
            matcher=lambda cmd: cmd.executable == "git" and cmd.subcommand in ["fetch", "pull", "clone"]
        ))

        # 5. GIT REMOTE PUSH & STATE CHANGE
        self.rules.append(Rule(
            name="GitRemotePush",
            description="Git push to remote repository",
            capabilities=[CapabilityType.GIT_REMOTE, CapabilityType.REMOTE_STATE_CHANGE, CapabilityType.NETWORK_ACCESS],
            score_delta=30,
            severity=SafetyClassification.MEDIUM_RISK,
            reversibility=Reversibility.PARTIALLY_REVERSIBLE,
            explanation="Modifies remote repository state over the network.",
            matcher=lambda cmd: cmd.executable == "git" and cmd.subcommand == "push" and not any(f in ["--force", "-f", "--force-with-lease"] for f in cmd.flags)
        ))

        # 6. GIT FORCE PUSH / DESTRUCTIVE RESET
        self.rules.append(Rule(
            name="GitDestructiveAction",
            description="Destructive Git reset, clean, or force push",
            capabilities=[CapabilityType.GIT_REMOTE, CapabilityType.REMOTE_STATE_CHANGE, CapabilityType.DELETE_FILESYSTEM],
            score_delta=55,
            severity=SafetyClassification.HIGH_RISK,
            reversibility=Reversibility.DIFFICULT_TO_REVERSE,
            explanation="Destructive Git operation (reset --hard, clean -fd, or force push).",
            matcher=lambda cmd: cmd.executable == "git" and (
                (cmd.subcommand == "reset" and any("hard" in f for f in cmd.flags)) or
                (cmd.subcommand == "clean" and any("f" in f for f in cmd.flags)) or
                (cmd.subcommand == "push" and any(f in ["--force", "-f", "--force-with-lease"] for f in cmd.flags))
            )
        ))

        # 7. PACKAGE INSTALLATION
        self.rules.append(Rule(
            name="PackageInstallation",
            description="Downloads and installs third-party software packages",
            capabilities=[CapabilityType.PACKAGE_INSTALLATION, CapabilityType.NETWORK_ACCESS, CapabilityType.WRITE_FILESYSTEM, CapabilityType.EXECUTE_PROCESS],
            score_delta=30,
            severity=SafetyClassification.MEDIUM_RISK,
            reversibility=Reversibility.PARTIALLY_REVERSIBLE,
            explanation="Downloads external packages and executes dependency lifecycle scripts.",
            matcher=lambda cmd: (
                (cmd.executable in ["pip", "pip3"] and cmd.subcommand in ["install", "upgrade"]) or
                (cmd.executable in ["npm", "pnpm"] and cmd.subcommand in ["install", "i", "add"]) or
                (cmd.executable == "yarn" and cmd.subcommand == "add") or
                (cmd.executable == "cargo" and cmd.subcommand == "add")
            )
        ))

        # 8. NETWORK ACCESS (CURL / WGET / FETCH)
        self.rules.append(Rule(
            name="NetworkTransfer",
            description="External network web request or file download",
            capabilities=[CapabilityType.NETWORK_ACCESS, CapabilityType.READ_FILESYSTEM],
            score_delta=15,
            severity=SafetyClassification.LOW_RISK,
            reversibility=Reversibility.REVERSIBLE,
            explanation="Executes external network HTTP/HTTPS request.",
            matcher=lambda cmd: cmd.executable in ["curl", "wget", "invoke-webrequest", "invoke-restmethod"]
        ))

        # 9. FILESYSTEM WRITE / CREATION
        self.rules.append(Rule(
            name="FilesystemWrite",
            description="Modifies or writes files to disk",
            capabilities=[CapabilityType.WRITE_FILESYSTEM],
            score_delta=15,
            severity=SafetyClassification.LOW_RISK,
            reversibility=Reversibility.PARTIALLY_REVERSIBLE,
            explanation="Modifies project files or writes output to disk.",
            matcher=lambda cmd: any(redir in cmd.raw_command for redir in [">", ">>", "Out-File", "Set-Content"])
        ))

        # 10. FILESYSTEM DELETION
        self.rules.append(Rule(
            name="FilesystemDeletion",
            description="Deletes files or directories",
            capabilities=[CapabilityType.DELETE_FILESYSTEM],
            score_delta=30,
            severity=SafetyClassification.MEDIUM_RISK,
            reversibility=Reversibility.PARTIALLY_REVERSIBLE,
            explanation="Deletes files or directory paths from disk.",
            matcher=lambda cmd: cmd.executable in ["rm", "del", "remove-item", "rmdir", "unlink"] and not any(f.lower() in ["-r", "-rf", "-recurse", "/s"] for f in cmd.flags)
        ))

        # 11. RECURSIVE DESTRUCTIVE DELETION
        self.rules.append(Rule(
            name="RecursiveDestructiveDeletion",
            description="Recursive destructive directory deletion",
            capabilities=[CapabilityType.DELETE_FILESYSTEM],
            score_delta=55,
            severity=SafetyClassification.HIGH_RISK,
            reversibility=Reversibility.IRREVERSIBLE,
            explanation="Recursively and forcefully deletes directory trees.",
            matcher=lambda cmd: cmd.executable in ["rm", "del", "remove-item", "rmdir"] and any(f.lower() in ["-r", "-rf", "-recurse", "/s", "-force"] for f in cmd.flags)
        ))

        # 12. CREDENTIAL & SECRET ACCESS
        self.rules.append(Rule(
            name="CredentialAccess",
            description="Inspects potential credential or secret files",
            capabilities=[CapabilityType.CREDENTIAL_ACCESS, CapabilityType.READ_FILESYSTEM],
            score_delta=40,
            severity=SafetyClassification.HIGH_RISK,
            reversibility=Reversibility.REVERSIBLE,
            explanation="Command attempts to read potential credential or secret storage locations.",
            matcher=lambda cmd: any(
                secret_word in target.lower() for target in (cmd.targets + cmd.args)
                for secret_word in [".env", ".ssh", "credentials", "secrets", "api_key", "token", "password"]
            )
        ))

        # 13. PRIVILEGE ESCALATION
        self.rules.append(Rule(
            name="PrivilegeEscalation",
            description="Executes process with elevated administrative privileges",
            capabilities=[CapabilityType.PRIVILEGE_ESCALATION, CapabilityType.SYSTEM_CONFIGURATION],
            score_delta=45,
            severity=SafetyClassification.HIGH_RISK,
            reversibility=Reversibility.PARTIALLY_REVERSIBLE,
            explanation="Requests administrative or superuser privileges.",
            matcher=lambda cmd: cmd.executable in ["sudo", "runas"] or any("runas" in f.lower() for f in cmd.flags)
        ))

        # 14. CRITICAL DESTRUCTIVE SYSTEM OPERATIONS
        self.rules.append(Rule(
            name="CriticalSystemDestruction",
            description="Destructive system, disk formatting, or database wipe operation",
            capabilities=[CapabilityType.DELETE_FILESYSTEM, CapabilityType.SYSTEM_CONFIGURATION],
            score_delta=80,
            severity=SafetyClassification.CRITICAL,
            reversibility=Reversibility.IRREVERSIBLE,
            explanation="High-impact system destruction, disk formatting, or database truncation command.",
            matcher=lambda cmd: (
                cmd.executable in ["format", "diskpart"]
            ) or (
                cmd.executable in ["rm", "remove-item"] and any(t in ["/", "c:\\", "c:/", "c:\\windows"] for t in [t.lower() for t in cmd.targets + cmd.args])
            ) or (
                any(db_kw in cmd.raw_command.upper() for db_kw in ["DROP DATABASE", "DROP TABLE", "TRUNCATE TABLE"])
            )
        ))

        # 15. OBFUSCATION / ENCODED EXECUTION
        self.rules.append(Rule(
            name="ObfuscatedExecution",
            description="Encoded or dynamically constructed obfuscated execution",
            capabilities=[CapabilityType.EXECUTE_PROCESS, CapabilityType.UNKNOWN_CAPABILITY],
            score_delta=40,
            severity=SafetyClassification.HIGH_RISK,
            reversibility=Reversibility.UNKNOWN,
            explanation="Command uses encoded payload flags (-EncodedCommand) or dynamic eval execution.",
            matcher=lambda cmd: any(f.lower() in ["-encodedcommand", "-enc", "base64", "eval"] for f in cmd.flags + cmd.args)
        ))


class RuleEngine:
    """Evaluates parsed commands against registered security rules."""

    def __init__(self, registry: Optional[SecurityRuleRegistry] = None):
        self.registry = registry or SecurityRuleRegistry()

    def evaluate(self, parsed_cmd: ParsedCommand) -> List[Tuple[Rule, str]]:
        """Evaluate command segments and return matched rules with explanations."""
        matched: List[Tuple[Rule, str]] = []

        cmds_to_eval = parsed_cmd.sub_commands if parsed_cmd.is_compound else [parsed_cmd]

        for cmd in cmds_to_eval:
            for rule in self.registry.rules:
                try:
                    if rule.matcher(cmd):
                        matched.append((rule, rule.explanation))
                except Exception:
                    continue

        return matched
