import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from policy.models import PolicyAssessment, PolicyDecision
from policy.approval import ApprovalManager, ApprovalStatus
from .models import EnforcementStatus, ExecutionMode, EnforcementRequest
from .result import EnforcementResult

logger = logging.getLogger("AegisEnforcementGate")


class EnforcementGate:
    """Aegis V0.7 Enforcement Gate translating Policy & Approval state into Enforcement decisions."""

    def __init__(
        self,
        approval_manager: Optional[ApprovalManager] = None,
        default_mode: ExecutionMode = ExecutionMode.SIMULATION,
    ):
        self.approval_manager = approval_manager or ApprovalManager()
        self.default_mode = default_mode

    def process(
        self,
        policy_assessment: PolicyAssessment,
        execution_mode: Optional[ExecutionMode] = None,
        event_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        enforcement_id: Optional[str] = None,
    ) -> EnforcementResult:
        mode = execution_mode or self.default_mode
        now_iso = datetime.now(timezone.utc).isoformat()

        req = EnforcementRequest.create(
            command=policy_assessment.command or "",
            policy_decision=policy_assessment.decision.value if isinstance(policy_assessment.decision, PolicyDecision) else str(policy_assessment.decision),
            policy_severity=policy_assessment.severity.value if hasattr(policy_assessment.severity, "value") else str(policy_assessment.severity),
            v03_risk=policy_assessment.v03_risk,
            approval_id=policy_assessment.approval_request_id,
            execution_mode=mode,
            event_id=event_id,
            session_id=session_id or policy_assessment.session_id,
            task_id=task_id or policy_assessment.task_id,
            enforcement_id=enforcement_id,
        )

        try:
            return self._evaluate_gate(policy_assessment, req, mode, now_iso)
        except Exception as err:
            logger.error(f"[Aegis Fail-Safe] Enforcement gate processing failed: {err}")
            return EnforcementResult(
                enforcement_id=req.enforcement_id,
                status=EnforcementStatus.FAILED,
                execution_mode=mode,
                policy_decision=req.policy_decision,
                policy_reasons=["Enforcement gate fail-safe triggered due to evaluation exception."],
                approval_id=req.approval_id,
                approval_status="FAILED",
                explanation=f"Fail-safe boundary caught error: {err}",
                timestamp=now_iso,
                command=req.command,
            )

    def _evaluate_gate(
        self,
        policy_assessment: PolicyAssessment,
        request: EnforcementRequest,
        mode: ExecutionMode,
        timestamp: str,
    ) -> EnforcementResult:
        decision_val = (
            policy_assessment.decision.value
            if isinstance(policy_assessment.decision, PolicyDecision)
            else str(policy_assessment.decision)
        )
        reasons_list = [r.explanation for r in policy_assessment.reasons]

        # RULE 1: Policy == BLOCK (Authoritative Block Invariant)
        if decision_val == PolicyDecision.BLOCK.value:
            return EnforcementResult(
                enforcement_id=request.enforcement_id,
                status=EnforcementStatus.BLOCKED,
                execution_mode=mode,
                policy_decision=decision_val,
                policy_reasons=reasons_list,
                approval_id=None,
                approval_status="NOT_AVAILABLE",
                explanation="Execution prohibited: command is blocked by Aegis security policy invariants.",
                timestamp=timestamp,
                command=request.command,
            )

        # RULE 2: Policy == ALLOW (Safe Automatic Execution)
        if decision_val == PolicyDecision.ALLOW.value:
            target_status = EnforcementStatus.SIMULATED if mode == ExecutionMode.SIMULATION else EnforcementStatus.ALLOWED
            return EnforcementResult(
                enforcement_id=request.enforcement_id,
                status=target_status,
                execution_mode=mode,
                policy_decision=decision_val,
                policy_reasons=reasons_list,
                approval_id=None,
                approval_status="AUTO_ALLOWED",
                explanation="Action permitted automatically by security policy without manual approval.",
                timestamp=timestamp,
                command=request.command,
            )

        # RULE 3: Policy == REVIEW (Human Approval Required)
        if decision_val == PolicyDecision.REVIEW.value:
            approval_req = self.approval_manager.find_approved_request(
                command=request.command,
                request_id=policy_assessment.approval_request_id,
                session_id=request.session_id,
                task_id=request.task_id,
            )

            if not approval_req and policy_assessment.approval_request_id:
                approval_req = self.approval_manager.get_request(policy_assessment.approval_request_id)

            if not approval_req:
                matching = [
                    r for r in self.approval_manager.list_requests()
                    if r.command == request.command
                ]
                if matching:
                    denied_matching = [r for r in matching if (r.status.value if hasattr(r.status, "value") else str(r.status)) == "DENIED"]
                    approval_req = denied_matching[0] if denied_matching else matching[0]

            if not approval_req:
                approval_req = self.approval_manager.create_request(
                    command=request.command,
                    risk_classification=policy_assessment.v03_risk or "UNKNOWN",
                    risk_score=policy_assessment.risk_score,
                    capabilities=[],
                    ai_verdict=policy_assessment.ai_verdict,
                    explanation=reasons_list[0] if reasons_list else "Human approval required.",
                    policy_reasons=[r.to_dict() for r in policy_assessment.reasons],
                    session_id=request.session_id,
                    task_id=request.task_id,
                )

            app_status_val = (
                approval_req.status.value
                if isinstance(approval_req.status, ApprovalStatus)
                else str(approval_req.status)
            )

            if app_status_val == ApprovalStatus.APPROVED.value:
                target_status = EnforcementStatus.SIMULATED if mode == ExecutionMode.SIMULATION else EnforcementStatus.ALLOWED
                return EnforcementResult(
                    enforcement_id=request.enforcement_id,
                    status=target_status,
                    execution_mode=mode,
                    policy_decision=decision_val,
                    policy_reasons=reasons_list,
                    approval_id=approval_req.request_id,
                    approval_status="APPROVED",
                    explanation="Human approval granted; action cleared for execution.",
                    timestamp=timestamp,
                    command=request.command,
                )

            elif app_status_val == ApprovalStatus.DENIED.value:
                return EnforcementResult(
                    enforcement_id=request.enforcement_id,
                    status=EnforcementStatus.DENIED,
                    execution_mode=mode,
                    policy_decision=decision_val,
                    policy_reasons=reasons_list,
                    approval_id=approval_req.request_id,
                    approval_status="DENIED",
                    explanation="Execution denied: human user explicitly denied approval.",
                    timestamp=timestamp,
                    command=request.command,
                )

            elif app_status_val in (ApprovalStatus.EXPIRED.value, ApprovalStatus.CANCELLED.value):
                return EnforcementResult(
                    enforcement_id=request.enforcement_id,
                    status=EnforcementStatus.DENIED,
                    execution_mode=mode,
                    policy_decision=decision_val,
                    policy_reasons=reasons_list,
                    approval_id=approval_req.request_id,
                    approval_status=app_status_val,
                    explanation=f"Execution prohibited: human approval request is {app_status_val.lower()}.",
                    timestamp=timestamp,
                    command=request.command,
                )

            else:  # PENDING
                return EnforcementResult(
                    enforcement_id=request.enforcement_id,
                    status=EnforcementStatus.WAITING_FOR_APPROVAL,
                    execution_mode=mode,
                    policy_decision=decision_val,
                    policy_reasons=reasons_list,
                    approval_id=approval_req.request_id,
                    approval_status="PENDING",
                    explanation="Action paused: waiting for explicit human approval.",
                    timestamp=timestamp,
                    command=request.command,
                )

        # Fallback
        return EnforcementResult(
            enforcement_id=request.enforcement_id,
            status=EnforcementStatus.FAILED,
            execution_mode=mode,
            policy_decision=decision_val,
            policy_reasons=reasons_list,
            approval_id=None,
            approval_status="UNKNOWN",
            explanation="Enforcement gate fallback: unrecognized policy decision.",
            timestamp=timestamp,
            command=request.command,
        )
