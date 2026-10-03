import re
from typing import Optional, List, Tuple, Set
from safety.models import SafetyAssessment, SafetyClassification, CapabilityType
from ai_supervisor.models import SupervisorAssessment, SupervisorVerdict
from ai_supervisor.routing_models import RoutingDecision
from supervisor.state import SessionState
from .models import PolicyDecision, PolicySeverity, PolicyReason
from .config import PolicyConfig, PolicyMode


class PolicyRuleEngine:
    """Deterministic policy rule engine combining V0.3, V0.4, V0.5, and SessionState."""

    @staticmethod
    def evaluate(
        command: str,
        safety_assessment: Optional[SafetyAssessment] = None,
        supervisor_assessment: Optional[SupervisorAssessment] = None,
        routing_decision: Optional[RoutingDecision] = None,
        session_state: Optional[SessionState] = None,
        config: Optional[PolicyConfig] = None,
    ) -> Tuple[PolicyDecision, PolicySeverity, List[PolicyReason]]:
        policy_config = config or PolicyConfig()
        reasons: List[PolicyReason] = []
        cmd_lower = (command or "").lower()

        risk_class = (
            safety_assessment.classification.value
            if safety_assessment and hasattr(safety_assessment.classification, "value")
            else (safety_assessment.classification if safety_assessment else "UNKNOWN")
        )
        risk_score = safety_assessment.score if safety_assessment else 0
        raw_capabilities = safety_assessment.capabilities if safety_assessment else []
        cap_strings: Set[str] = {c.value if hasattr(c, "value") else str(c) for c in raw_capabilities}

        ai_verdict = None
        if supervisor_assessment:
            if hasattr(supervisor_assessment, "verdict") and supervisor_assessment.verdict is not None:
                ai_verdict = (
                    supervisor_assessment.verdict.value
                    if hasattr(supervisor_assessment.verdict, "value")
                    else str(supervisor_assessment.verdict)
                )
            else:
                ai_verdict = "UNKNOWN"
        else:
            ai_verdict = "UNAVAILABLE"

        # ----------------------------------------------------
        # PRECEDENCE LEVEL 0: Supervisor Tampering Protection (Human-Only Invariant)
        # ----------------------------------------------------
        if re.search(r'--protection-off|uninstall-interceptor|--disable-aegis|protection_state\.json', cmd_lower):
            reasons.append(PolicyReason(
                rule_id="POL-000",
                severity=PolicySeverity.CRITICAL,
                title="Supervisor Protection Tampering Attempt",
                explanation="Antigravity agent is strictly prohibited from disabling Aegis protection or tampering with state files."
            ))
            return PolicyDecision.BLOCK, PolicySeverity.CRITICAL, reasons

        # ----------------------------------------------------
        # PRECEDENCE LEVEL 1: CRITICAL Deterministic Findings & Database Destruction & Destructive Operations
        # ----------------------------------------------------
        if risk_class == SafetyClassification.CRITICAL.value:
            reasons.append(PolicyReason(
                rule_id="POL-001",
                severity=PolicySeverity.CRITICAL,
                title="Critical Technical Safety Risk",
                explanation="Action classified as CRITICAL by deterministic safety engine."
            ))
            return PolicyDecision.BLOCK, PolicySeverity.CRITICAL, reasons

        if re.search(r'\b(drop\s+database|drop\s+table|truncate\s+table|truncate)\b', cmd_lower):
            reasons.append(PolicyReason(
                rule_id="POL-002",
                severity=PolicySeverity.CRITICAL,
                title="Database Destruction Operation",
                explanation="Destructive database operations are strictly blocked by security policy."
            ))
            return PolicyDecision.BLOCK, PolicySeverity.CRITICAL, reasons

        if re.search(r'rm\s+-rf\s+[\/\*]|del\s+/s\s+c:\\windows|rd\s+/s\s+/q\s+c:\\', cmd_lower):
            reasons.append(PolicyReason(
                rule_id="POL-003",
                severity=PolicySeverity.CRITICAL,
                title="Root Destructive Filesystem Operation",
                explanation="Broad destructive filesystem operation targeting root or system directories."
            ))
            return PolicyDecision.BLOCK, PolicySeverity.CRITICAL, reasons

        # ----------------------------------------------------
        # PRECEDENCE LEVEL 2: Destructive Capabilities (DELETE_FILESYSTEM with high risk)
        # ----------------------------------------------------
        if (CapabilityType.DELETE_FILESYSTEM.value in cap_strings or CapabilityType.DELETE_FILESYSTEM in raw_capabilities) and (risk_score >= 70 or "rm -rf" in cmd_lower or "git reset --hard" in cmd_lower):
            reasons.append(PolicyReason(
                rule_id="POL-004",
                severity=PolicySeverity.HIGH,
                title="Destructive Filesystem Operation",
                explanation="Destructive disk operation requires explicit policy blocking."
            ))
            return PolicyDecision.BLOCK, PolicySeverity.HIGH, reasons

        # ----------------------------------------------------
        # PRECEDENCE LEVEL 3: Credential Access & Exfiltration
        # ----------------------------------------------------
        is_cred_access = (
            CapabilityType.CREDENTIAL_ACCESS.value in cap_strings
            or CapabilityType.CREDENTIAL_ACCESS in raw_capabilities
            or re.search(r'\.env|id_rsa|\b(token|secret|password|pem|auth)\b', cmd_lower)
        )
        if is_cred_access:
            if re.search(r'\b(curl|wget|nc|netcat|http|ftp|scp)\b', cmd_lower):  # exfiltration pattern
                reasons.append(PolicyReason(
                    rule_id="POL-005A",
                    severity=PolicySeverity.CRITICAL,
                    title="Potential Credential Exfiltration",
                    explanation="Credential access combined with network transfer indicates potential exfiltration."
                ))
                return PolicyDecision.BLOCK, PolicySeverity.CRITICAL, reasons
            else:
                if policy_config.mode == PolicyMode.STRICT:
                    reasons.append(PolicyReason(
                        rule_id="POL-005B",
                        severity=PolicySeverity.HIGH,
                        title="Credential Access (Strict Policy)",
                        explanation="Credential file access requires human approval under STRICT policy."
                    ))
                    return PolicyDecision.REVIEW, PolicySeverity.HIGH, reasons
                else:
                    reasons.append(PolicyReason(
                        rule_id="POL-005C",
                        severity=PolicySeverity.MEDIUM,
                        title="Credential File Access",
                        explanation="Credential access detected; requires human review."
                    ))
                    return PolicyDecision.REVIEW, PolicySeverity.MEDIUM, reasons

        # ----------------------------------------------------
        # PRECEDENCE LEVEL 4: Privilege Escalation & System Configuration
        # ----------------------------------------------------
        if (CapabilityType.PRIVILEGE_ESCALATION.value in cap_strings or CapabilityType.PRIVILEGE_ESCALATION in raw_capabilities) or re.search(r'\b(sudo|su|runas|set-executionpolicy)\b', cmd_lower):
            reasons.append(PolicyReason(
                rule_id="POL-006",
                severity=PolicySeverity.HIGH,
                title="Privilege Escalation Request",
                explanation="Administrative privilege escalation requires explicit human review."
            ))
            return PolicyDecision.REVIEW, PolicySeverity.HIGH, reasons

        if (CapabilityType.SYSTEM_CONFIGURATION.value in cap_strings or CapabilityType.SYSTEM_CONFIGURATION in raw_capabilities) or re.search(r'\/etc\/|c:\\windows', cmd_lower):
            reasons.append(PolicyReason(
                rule_id="POL-007",
                severity=PolicySeverity.HIGH,
                title="System Configuration Change",
                explanation="Modifying system-level configuration files requires review."
            ))
            return PolicyDecision.REVIEW, PolicySeverity.HIGH, reasons

        # ----------------------------------------------------
        # PRECEDENCE LEVEL 5: HIGH_RISK Findings & Force Push & Unknown Capabilities
        # ----------------------------------------------------
        if risk_class == SafetyClassification.HIGH_RISK.value:
            reasons.append(PolicyReason(
                rule_id="POL-008",
                severity=PolicySeverity.HIGH,
                title="High Technical Safety Risk",
                explanation="HIGH_RISK action requires human approval before proceeding."
            ))
            return PolicyDecision.REVIEW, PolicySeverity.HIGH, reasons

        if re.search(r'git.*push.*(--force|-f|\bforce\b)', cmd_lower):
            reasons.append(PolicyReason(
                rule_id="POL-009",
                severity=PolicySeverity.HIGH,
                title="Git Force Push Operation",
                explanation="Overwriting remote repository history via force push requires human review."
            ))
            return PolicyDecision.REVIEW, PolicySeverity.HIGH, reasons

        if CapabilityType.UNKNOWN_CAPABILITY.value in cap_strings or CapabilityType.UNKNOWN_CAPABILITY in raw_capabilities:
            reasons.append(PolicyReason(
                rule_id="POL-010",
                severity=PolicySeverity.MEDIUM,
                title="Unknown Action Capability",
                explanation="Unrecognized tool or capability requires human verification."
            ))
            return PolicyDecision.REVIEW, PolicySeverity.MEDIUM, reasons

        # ----------------------------------------------------
        # PRECEDENCE LEVEL 6: AI Contextual Concerns & Disagreement Overrides
        # ----------------------------------------------------
        if ai_verdict == SupervisorVerdict.SUSPICIOUS.value:
            reasons.append(PolicyReason(
                rule_id="POL-011",
                severity=PolicySeverity.HIGH,
                title="Suspicious AI Contextual Assessment",
                explanation="AI supervisor flagged this action as contextually suspicious."
            ))
            return PolicyDecision.REVIEW, PolicySeverity.HIGH, reasons

        if ai_verdict in (SupervisorVerdict.QUESTIONABLE.value, SupervisorVerdict.NEEDS_HUMAN_REVIEW.value):
            reasons.append(PolicyReason(
                rule_id="POL-012",
                severity=PolicySeverity.MEDIUM,
                title="Questionable AI Contextual Assessment",
                explanation="AI supervisor flagged action alignment as questionable or requiring human review."
            ))
            return PolicyDecision.REVIEW, PolicySeverity.MEDIUM, reasons

        # ----------------------------------------------------
        # PRECEDENCE LEVEL 7: Medium Risk Handling by Policy Mode
        # ----------------------------------------------------
        if risk_class == SafetyClassification.MEDIUM_RISK.value:
            if policy_config.mode in (PolicyMode.STRICT, PolicyMode.BALANCED):
                reasons.append(PolicyReason(
                    rule_id="POL-013A",
                    severity=PolicySeverity.MEDIUM,
                    title="Medium Safety Risk (Review Required)",
                    explanation="MEDIUM_RISK action requires review under current policy mode."
                ))
                return PolicyDecision.REVIEW, PolicySeverity.MEDIUM, reasons
            else:  # PERMISSIVE
                reasons.append(PolicyReason(
                    rule_id="POL-013B",
                    severity=PolicySeverity.LOW,
                    title="Medium Safety Risk (Permissive Allow)",
                    explanation="MEDIUM_RISK action permitted under PERMISSIVE policy mode."
                ))
                return PolicyDecision.ALLOW, PolicySeverity.LOW, reasons

        # ----------------------------------------------------
        # PRECEDENCE LEVEL 8: Routine Safe & Low Risk Actions
        # ----------------------------------------------------
        if risk_class in (SafetyClassification.SAFE.value, SafetyClassification.LOW_RISK.value):
            reasons.append(PolicyReason(
                rule_id="POL-014",
                severity=PolicySeverity.INFORMATIONAL if risk_class == SafetyClassification.SAFE.value else PolicySeverity.LOW,
                title="Routine Safe Action",
                explanation="Action is routine, safe, and contextually aligned; policy permits execution."
            ))
            return PolicyDecision.ALLOW, PolicySeverity.INFORMATIONAL if risk_class == SafetyClassification.SAFE.value else PolicySeverity.LOW, reasons

        # Fallback default
        reasons.append(PolicyReason(
            rule_id="POL-999",
            severity=PolicySeverity.MEDIUM,
            title="Unspecified Action Fallback",
            explanation="Unspecified risk action routed to review by safety default."
        ))
        return PolicyDecision.REVIEW, PolicySeverity.MEDIUM, reasons
