import os
from typing import Optional, List, Set
from datetime import datetime, timezone
from .models import (
    SafetyClassification, SafetyAction, CapabilityType, Reversibility, Scope, SafetyAssessment
)
from .patterns import CommandParser, ParsedCommand
from .rules import RuleEngine, Rule
from supervisor.state import SessionState, TaskState


class SafetyAnalyzer:
    """Deterministic risk scoring, capability taxonomy, and context-aware security analyzer."""

    def __init__(self, rule_engine: Optional[RuleEngine] = None):
        self.parser = CommandParser()
        self.rule_engine = rule_engine or RuleEngine()

    def analyze(
        self,
        command: str,
        session_state: Optional[SessionState] = None,
        task_state: Optional[TaskState] = None
    ) -> SafetyAssessment:
        """Perform deterministic security analysis on a command string (Data only; no execution)."""
        cmd_clean = (command or "").strip()
        timestamp = datetime.now(timezone.utc).isoformat()

        if not cmd_clean:
            return SafetyAssessment(
                command="",
                classification=SafetyClassification.SAFE,
                action=SafetyAction.OBSERVE,
                score=0,
                reasons=["Empty command provided."],
                capabilities=[],
                reversibility=Reversibility.REVERSIBLE,
                scope=Scope.UNKNOWN,
                confidence="HIGH",
                timestamp=timestamp
            )

        parsed_cmd = self.parser.parse(cmd_clean)
        matched = self.rule_engine.evaluate(parsed_cmd)

        capabilities_set: Set[CapabilityType] = set()
        matched_rule_names: List[str] = []
        reasons: List[str] = []
        raw_score = 0
        worst_reversibility = Reversibility.REVERSIBLE

        reversibility_priority = {
            Reversibility.REVERSIBLE: 1,
            Reversibility.PARTIALLY_REVERSIBLE: 2,
            Reversibility.DIFFICULT_TO_REVERSE: 3,
            Reversibility.UNKNOWN: 4,
            Reversibility.IRREVERSIBLE: 5,
        }

        for rule, exp in matched:
            matched_rule_names.append(rule.name)
            capabilities_set.update(rule.capabilities)
            raw_score += rule.score_delta
            reasons.append(exp)

            if reversibility_priority.get(rule.reversibility, 1) > reversibility_priority.get(worst_reversibility, 1):
                worst_reversibility = rule.reversibility

        # Default capability if none matched
        if not capabilities_set:
            capabilities_set.add(CapabilityType.EXECUTE_PROCESS)

        # Evaluate Project Scope
        scope = self._evaluate_scope(parsed_cmd, session_state)
        if scope == Scope.OUTSIDE_PROJECT:
            raw_score += 20
            capabilities_set.add(CapabilityType.WRITE_FILESYSTEM)
            reasons.append("Command targets filesystem locations outside current project workspace.")

        # Context-aware adjustments
        confidence = "HIGH"
        if parsed_cmd.is_compound:
            reasons.append(f"Compound command containing {len(parsed_cmd.sub_commands)} chained segments.")

        if session_state and session_state.current_phase == "VERIFICATION":
            if "SafeReadCommands" in matched_rule_names:
                reasons.append("Command aligns with current VERIFICATION workflow phase.")

        # Final Score to Classification Mapping
        classification, action = self._classify_score(raw_score)

        return SafetyAssessment(
            command=cmd_clean,
            classification=classification,
            action=action,
            score=max(0, raw_score),
            reasons=reasons if reasons else ["Standard process execution command."],
            capabilities=list(capabilities_set),
            reversibility=worst_reversibility,
            scope=scope,
            confidence=confidence,
            matched_rules=matched_rule_names,
            timestamp=timestamp,
            session_id=session_state.session_id if session_state else None,
            task_id=task_state.task_id if task_state else (session_state.active_task_id if session_state else None)
        )

    def _evaluate_scope(self, parsed_cmd: ParsedCommand, session_state: Optional[SessionState]) -> Scope:
        """Determine whether targets are INSIDE_PROJECT or OUTSIDE_PROJECT."""
        targets = parsed_cmd.targets
        if not targets:
            return Scope.INSIDE_PROJECT

        for t in targets:
            t_clean = t.replace("\\", "/").lower()
            if t_clean.startswith("c:/windows") or t_clean.startswith("c:/system") or t_clean.startswith("/usr") or t_clean.startswith("/bin") or t_clean == "/" or t_clean == "c:":
                return Scope.OUTSIDE_PROJECT

        return Scope.INSIDE_PROJECT

    def _classify_score(self, score: int) -> (SafetyClassification, SafetyAction):
        """Map score to SafetyClassification and SafetyAction analytical labels."""
        if score <= 10:
            return SafetyClassification.SAFE, SafetyAction.OBSERVE
        elif score <= 25:
            return SafetyClassification.LOW_RISK, SafetyAction.OBSERVE
        elif score <= 49:
            return SafetyClassification.MEDIUM_RISK, SafetyAction.REVIEW_REQUIRED
        elif score <= 75:
            return SafetyClassification.HIGH_RISK, SafetyAction.REVIEW_REQUIRED
        else:
            return SafetyClassification.CRITICAL, SafetyAction.RESTRICTED
