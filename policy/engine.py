import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from safety.models import SafetyAssessment, SafetyClassification
from ai_supervisor.models import SupervisorAssessment
from ai_supervisor.routing_models import RoutingDecision
from supervisor.state import SessionState
from .models import PolicyDecision, PolicySeverity, PolicyReason, PolicyAssessment
from .config import PolicyConfig
from .rules import PolicyRuleEngine
from .approval import ApprovalManager, ApprovalStatus
from .audit import AuditLogger

logger = logging.getLogger("AegisPolicyEngine")


class PolicyEngine:
    """Aegis V0.6 Policy Decision & Approval Engine."""

    def __init__(
        self,
        config: Optional[PolicyConfig] = None,
        approval_manager: Optional[ApprovalManager] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.config = config or PolicyConfig.from_env_or_dict()
        self.approval_manager = approval_manager or ApprovalManager()
        self.audit_logger = audit_logger or AuditLogger()

    def evaluate(
        self,
        command: str,
        safety_assessment: Optional[SafetyAssessment] = None,
        supervisor_assessment: Optional[SupervisorAssessment] = None,
        routing_decision: Optional[RoutingDecision] = None,
        session_state: Optional[SessionState] = None,
        event_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> PolicyAssessment:
        now_iso = datetime.now(timezone.utc).isoformat()
        sess_id = session_id or (session_state.session_id if session_state else None)
        tsk_id = task_id or (session_state.active_task_id if session_state else None)

        # Fail-Safe Boundary: Catch any unexpected exceptions and default to REVIEW or BLOCK
        try:
            decision, severity, reasons = PolicyRuleEngine.evaluate(
                command=command,
                safety_assessment=safety_assessment,
                supervisor_assessment=supervisor_assessment,
                routing_decision=routing_decision,
                session_state=session_state,
                config=self.config,
            )
        except Exception as err:
            logger.error(f"[Aegis Fail-Safe] Policy evaluation failed: {err}")
            # Fail-safe decision: Default to REVIEW with HIGH severity
            decision = PolicyDecision.REVIEW
            severity = PolicySeverity.HIGH
            reasons = [
                PolicyReason(
                    rule_id="POL-FAILSAFE",
                    severity=PolicySeverity.HIGH,
                    title="Policy Engine Fail-Safe Triggered",
                    explanation=f"Policy evaluation encountered an unexpected error ({err}); defaulted to REVIEW."
                )
            ]

        v03_risk = (
            safety_assessment.classification.value
            if safety_assessment and hasattr(safety_assessment.classification, "value")
            else (safety_assessment.classification if safety_assessment else "UNKNOWN")
        )
        risk_score = safety_assessment.score if safety_assessment else 0
        raw_caps = safety_assessment.capabilities if safety_assessment else []
        capabilities = [c.value if hasattr(c, "value") else str(c) for c in raw_caps]

        ai_verdict = (
            supervisor_assessment.verdict.value
            if supervisor_assessment and hasattr(supervisor_assessment.verdict, "value")
            else (supervisor_assessment.verdict if supervisor_assessment else None)
        )
        route_str = (
            routing_decision.route.value
            if routing_decision and hasattr(routing_decision.route, "value")
            else (routing_decision.route if routing_decision else None)
        )

        approval_req_id = None
        is_already_approved = False
        if decision == PolicyDecision.REVIEW:
            # Check if there is an existing approved request
            existing_approved = self.approval_manager.find_approved_request(
                command=command,
                session_id=sess_id,
                task_id=tsk_id,
            )
            if existing_approved:
                approval_req_id = existing_approved.request_id
                is_already_approved = True
            else:
                existing_reqs = [
                    r for r in self.approval_manager.list_requests()
                    if r.command == command
                ]
                if existing_reqs:
                    denied_reqs = [r for r in existing_reqs if (r.status.value if hasattr(r.status, "value") else str(r.status)) == "DENIED"]
                    if denied_reqs:
                        approval_req_id = denied_reqs[0].request_id
                    else:
                        approval_req_id = existing_reqs[0].request_id
                else:
                    policy_reasons_dict = [r.to_dict() for r in reasons]
                    phase_str = session_state.current_phase if session_state else None
                    req = self.approval_manager.create_request(
                        command=command,
                        risk_classification=v03_risk,
                        risk_score=risk_score,
                        capabilities=capabilities,
                        ai_verdict=ai_verdict,
                        explanation=reasons[0].explanation if reasons else "Review required by security policy.",
                        policy_reasons=policy_reasons_dict,
                        session_id=sess_id,
                        task_id=tsk_id,
                        workflow_phase=phase_str,
                        reason_for_review=reasons[0].explanation if reasons else "Review required by security policy.",
                        policy_decision="REVIEW",
                    )
                    approval_req_id = req.request_id

        assessment = PolicyAssessment(
            decision=decision,
            severity=severity,
            reasons=reasons,
            risk_score=risk_score,
            ai_verdict=ai_verdict,
            routing_decision=route_str,
            confidence="HIGH",
            policy_version="0.6.0",
            timestamp=now_iso,
            command=command,
            session_id=sess_id,
            task_id=tsk_id,
            approval_request_id=approval_req_id,
            v03_risk=v03_risk,
        )

        audit_decision = "PERMITTED" if is_already_approved else (decision.value if isinstance(decision, PolicyDecision) else str(decision))
        audit_app_status = "APPROVED" if is_already_approved else ("PENDING" if decision == PolicyDecision.REVIEW else ("NOT_APPLICABLE" if decision == PolicyDecision.BLOCK else "AUTO_ALLOWED"))
        audit_reasons = [f"Human approval granted (Request ID: {approval_req_id}); cleared for execution."] if is_already_approved else [r.explanation for r in reasons]

        # Record decision in secret-redacted audit log
        self.audit_logger.log(
            command=command,
            v03_risk=v03_risk,
            risk_score=risk_score,
            capabilities=capabilities,
            final_policy_decision=audit_decision,
            policy_reasons=audit_reasons,
            event_id=event_id,
            session_id=sess_id,
            task_id=tsk_id,
            v04_verdict=ai_verdict,
            v04_confidence=supervisor_assessment.confidence if supervisor_assessment else None,
            v05_route=route_str,
            approval_status=audit_app_status,
            policy_version="0.6.0",
        )

        return assessment
