import re
from typing import Optional, Tuple
from safety.models import SafetyAssessment, CapabilityType
from supervisor.session import SessionState
from supervisor.phase import WorkflowPhase
from .routing_models import SensitivityLevel


class ComplexityScorer:
    """Computes a deterministic complexity score (0-100) for a command and its context."""

    @staticmethod
    def calculate(
        command: str,
        safety_assessment: Optional[SafetyAssessment] = None,
        session_state: Optional[SessionState] = None
    ) -> int:
        score = 0
        cmd_lower = command.lower()

        # 1. Chained & compound commands / pipelines
        chain_operators = re.findall(r'(&&|\|\||;)', command)
        if len(chain_operators) == 1:
            score += 15
        elif len(chain_operators) > 1:
            score += 25

        if "|" in command:
            score += 15

        # 2. Shell nesting / subshells
        if re.search(r'\$\(|=|`|powershell(\.exe)?\s+-c|bash\s+-c|cmd\s+/c|sh\s+-c', cmd_lower):
            score += 20

        # 3. Dangerous / unusual flags
        if re.search(r'--(no-verify|force|insecure|allow-unauthenticated)|-[fky]\b|-rf\b|--yes\b', cmd_lower):
            score += 15

        # 4. Script execution & piped downloads
        if re.search(r'curl.*\|.*(sh|powershell|bash)|python\b|node\b|powershell\b|bash\b|\.(sh|ps1|bat)\b', cmd_lower):
            score += 25

        # 5. Package installation
        has_pkg_cap = (
            safety_assessment
            and CapabilityType.PACKAGE_INSTALLATION in safety_assessment.capabilities
        )
        if has_pkg_cap or re.search(r'\b(npm|pip|cargo|go|apt-get|apt|brew|choco|yarn|pnpm)\s+(install|add|get)\b', cmd_lower):
            score += 20

        # 6. Network access
        has_net_cap = (
            safety_assessment
            and CapabilityType.NETWORK_ACCESS in safety_assessment.capabilities
        )
        if has_net_cap or re.search(r'\b(curl|wget|ssh|scp|ftp|nc|netcat|git clone|git fetch|git pull|git push)\b|https?://', cmd_lower):
            score += 20

        # 7. Remote state changes
        has_remote_cap = (
            safety_assessment
            and (
                CapabilityType.REMOTE_STATE_CHANGE in safety_assessment.capabilities
                or CapabilityType.GIT_REMOTE in safety_assessment.capabilities
            )
        )
        if has_remote_cap or re.search(r'\b(git push|kubectl apply|terraform apply|aws|gcloud|docker push)\b', cmd_lower):
            score += 25

        # 8. Filesystem scope & destruction
        has_del_cap = (
            safety_assessment
            and CapabilityType.DELETE_FILESYSTEM in safety_assessment.capabilities
        )
        if has_del_cap or re.search(r'rm\s+-rf|del\s+/s|rd\s+/s|\/etc\/|\/usr\/|c:\\windows', cmd_lower):
            score += 25

        # 9. Database operations
        has_db_cap = (
            safety_assessment
            and (
                CapabilityType.DATABASE_WRITE in safety_assessment.capabilities
                or CapabilityType.DATABASE_READ in safety_assessment.capabilities
            )
        )
        if has_db_cap or re.search(r'\b(drop|truncate|delete from|alter table|mongo|psql|mysql)\b', cmd_lower):
            score += 25

        # 10. Privilege changes
        has_priv_cap = (
            safety_assessment
            and CapabilityType.PRIVILEGE_ESCALATION in safety_assessment.capabilities
        )
        if has_priv_cap or re.search(r'\b(sudo|su|chmod|chown|runas|set-executionpolicy)\b', cmd_lower):
            score += 25

        # 11. Credential activity
        has_cred_cap = (
            safety_assessment
            and CapabilityType.CREDENTIAL_ACCESS in safety_assessment.capabilities
        )
        if has_cred_cap or re.search(r'\.env|id_rsa|\b(token|secret|password|pem|auth|key)\b', cmd_lower):
            score += 20

        # 12. Unknown capabilities
        if safety_assessment and CapabilityType.UNKNOWN_CAPABILITY in safety_assessment.capabilities:
            score += 30

        return min(max(score, 0), 100)


class UncertaintyScorer:
    """Computes a deterministic uncertainty score (0-100) based on context signals."""

    @staticmethod
    def calculate(
        command: str,
        safety_assessment: Optional[SafetyAssessment] = None,
        session_state: Optional[SessionState] = None
    ) -> int:
        score = 0
        cmd_lower = command.lower()

        # 1. Unknown capability in safety assessment
        if safety_assessment and CapabilityType.UNKNOWN_CAPABILITY in safety_assessment.capabilities:
            score += 35

        # 2. Parser ambiguity / empty / unrecognized command structure
        if not command.strip() or (safety_assessment and "UNKNOWN_CAPABILITY" in safety_assessment.matched_rules):
            score += 25

        # 3. Session state signals
        if session_state:
            # Missing session goal
            if not session_state.current_goal:
                score += 30

            # Missing task context
            if not session_state.tasks:
                score += 10

            # Insufficient command history
            if len(session_state.commands) <= 1:
                score += 10

            # Command inconsistent with current workflow phase
            phase = session_state.current_phase
            if phase in (WorkflowPhase.RESEARCH.value, WorkflowPhase.PLANNING.value):
                if re.search(r'\b(git push|kubectl|terraform|docker push|rm -rf|del /s)\b', cmd_lower):
                    score += 30
                elif re.search(r'\b(npm install|pip install|cargo install)\b', cmd_lower):
                    score += 20
            elif phase == WorkflowPhase.VERIFICATION.value:
                if re.search(r'\b(drop|truncate|alter table|c:\\windows|\/etc\/)\b', cmd_lower):
                    score += 25

            # Contextual Goal Mismatch Signal
            # Example: User goal is building frontend, but command downloads/executes remote scripts
            goal_lower = (session_state.current_goal or "").lower()
            if goal_lower:
                if ("react" in goal_lower or "frontend" in goal_lower or "ui" in goal_lower) and (
                    "curl" in cmd_lower or "wget" in cmd_lower or "|" in cmd_lower or "powershell" in cmd_lower
                ):
                    score += 35

        return min(max(score, 0), 100)


class SensitivityMultiplier:
    """Determines action sensitivity score and level for routing escalation."""

    @staticmethod
    def evaluate(
        command: str,
        safety_assessment: Optional[SafetyAssessment] = None
    ) -> Tuple[SensitivityLevel, int]:
        cmd_lower = command.lower()
        score = 0
        level = SensitivityLevel.LOW

        # Database destruction or system config modifications -> CRITICAL
        if re.search(r'\bdrop\s+database\b|\bdrop\s+table\b|\btruncate\b', cmd_lower) or (
            safety_assessment and CapabilityType.SYSTEM_CONFIGURATION in safety_assessment.capabilities
        ) or re.search(r'set-executionpolicy|\/etc\/|c:\\windows', cmd_lower):
            score = max(score, 95)
            level = SensitivityLevel.CRITICAL

        # Force push -> CRITICAL
        if re.search(r'git\s+push.*--force\b|git\s+push.*-f\b', cmd_lower):
            score = max(score, 90)
            level = SensitivityLevel.CRITICAL

        # Destructive disk ops or privilege escalation -> HIGH / CRITICAL
        if re.search(r'rm\s+-rf|del\s+/s|rd\s+/s|git\s+reset\s+--hard', cmd_lower) or (
            safety_assessment and CapabilityType.DELETE_FILESYSTEM in safety_assessment.capabilities
        ):
            score = max(score, 75)
            if level != SensitivityLevel.CRITICAL:
                level = SensitivityLevel.HIGH

        if re.search(r'\b(sudo|runas)\b', cmd_lower) or (
            safety_assessment and CapabilityType.PRIVILEGE_ESCALATION in safety_assessment.capabilities
        ):
            score = max(score, 75)
            if level != SensitivityLevel.CRITICAL:
                level = SensitivityLevel.HIGH

        # Credential access or remote state change -> HIGH
        if re.search(r'\.env|id_rsa|\b(token|secret|password|pem|auth)\b', cmd_lower) or (
            safety_assessment and CapabilityType.CREDENTIAL_ACCESS in safety_assessment.capabilities
        ):
            score = max(score, 70)
            if level != SensitivityLevel.CRITICAL:
                level = SensitivityLevel.HIGH

        if re.search(r'\b(git push|kubectl apply|terraform apply|aws|gcloud|docker push)\b', cmd_lower) or (
            safety_assessment and (
                CapabilityType.REMOTE_STATE_CHANGE in safety_assessment.capabilities or
                CapabilityType.GIT_REMOTE in safety_assessment.capabilities
            )
        ):
            score = max(score, 65)
            if level != SensitivityLevel.CRITICAL:
                level = SensitivityLevel.HIGH

        # Unknown capabilities -> HIGH
        if safety_assessment and CapabilityType.UNKNOWN_CAPABILITY in safety_assessment.capabilities:
            score = max(score, 60)
            if level != SensitivityLevel.CRITICAL:
                level = SensitivityLevel.HIGH

        # Baseline sensitivity evaluation
        if score == 0:
            if re.search(r'\bgit\s+(status|log|diff|branch|show|tag|rev-parse)\b', cmd_lower):
                score = 10
                level = SensitivityLevel.LOW
            elif re.search(r'\b(npm|pip|cargo|python|node|git|make|docker)\b', cmd_lower):
                score = 30
                level = SensitivityLevel.MEDIUM
            else:
                score = 10
                level = SensitivityLevel.LOW

        return level, score
