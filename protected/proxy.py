import os
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from supervisor.state import SessionState
from safety.analyzer import SafetyAnalyzer
from ai_supervisor.supervisor import AISupervisor
from ai_supervisor.router import ModelRouter
from ai_supervisor.sanitizer import ContextSanitizer
from policy.engine import PolicyEngine
from policy.config import PolicyConfig
from policy.approval import ApprovalManager, ApprovalStatus
from policy.models import PolicyDecision
from policy.audit import AuditLogger
from enforcement.gate import EnforcementGate
from enforcement.executor import ExecutorFactory, CommandExecutor
from enforcement.models import ExecutionMode, EnforcementStatus
from .models import GatewayStatus, ProtectedContext, ProtectedResponse, WorkspaceBoundary
from .gateway import ProtectedGateway
from .session import ProtectedSession

from .protection import ProtectionManager

logger = logging.getLogger("AegisCommandProxy")


class CommandProxy:
    """Aegis V0.8 Command Proxy mediating proposed tool/command execution before enforcement."""

    def __init__(
        self,
        workspace_boundary: Optional[WorkspaceBoundary] = None,
        policy_engine: Optional[PolicyEngine] = None,
        approval_manager: Optional[ApprovalManager] = None,
        audit_logger: Optional[AuditLogger] = None,
        protection_manager: Optional[ProtectionManager] = None,
        default_mode: ExecutionMode = ExecutionMode.SIMULATION,
    ):
        self.boundary = workspace_boundary or WorkspaceBoundary(workspace_root=os.getcwd())
        self.gateway = ProtectedGateway(workspace_boundary=self.boundary)
        self.approval_manager = approval_manager or ApprovalManager()
        self.audit_logger = audit_logger or AuditLogger()
        self.protection_manager = protection_manager or ProtectionManager()
        self.policy_engine = policy_engine or PolicyEngine(
            config=PolicyConfig.from_env_or_dict(),
            approval_manager=self.approval_manager,
            audit_logger=self.audit_logger,
        )
        self.enforcement_gate = EnforcementGate(
            approval_manager=self.approval_manager,
            default_mode=default_mode,
        )
        self.safety_analyzer = SafetyAnalyzer()
        self.ai_supervisor = AISupervisor()
        self.model_router = ModelRouter()
        self.sanitizer = ContextSanitizer()

    def submit(
        self,
        command: str,
        context: Optional[ProtectedContext] = None,
        session_state: Optional[SessionState] = None,
        execution_mode: Optional[ExecutionMode] = None,
        event_id: Optional[str] = None,
    ) -> ProtectedResponse:
        now_iso = datetime.now(timezone.utc).isoformat()
        mode = execution_mode or self.enforcement_gate.default_mode
        clean_cmd = self.sanitizer.redact_secrets(command or "")
        prot_ctx = context or ProtectedContext(workspace_root=self.boundary.workspace_root)

        if not self.protection_manager.is_protection_on():
            return ProtectedResponse(
                gateway_status=GatewayStatus.PASSTHROUGH,
                command=clean_cmd,
                policy_decision="PASSTHROUGH",
                enforcement_status="PASSTHROUGH",
                reasons=["Aegis Protection is explicitly OFF."],
                explanation="Protection is OFF; command permitted by human override.",
                timestamp=now_iso,
                event_id=event_id,
                session_id=prot_ctx.session_id,
                task_id=prot_ctx.task_id,
            )

        try:
            return self._process_submission(
                command=clean_cmd,
                context=prot_ctx,
                session_state=session_state,
                mode=mode,
                event_id=event_id,
                timestamp=now_iso,
            )
        except Exception as err:
            logger.error(f"[Aegis Fail-Safe] CommandProxy submission failed: {err}")
            return ProtectedResponse(
                gateway_status=GatewayStatus.FAILED_GATEWAY,
                command=clean_cmd,
                policy_decision="ERROR",
                enforcement_status="FAILED",
                reasons=["Fail-safe boundary caught exception during proxy submission."],
                explanation=f"Fail-safe error: {err}",
                timestamp=now_iso,
                event_id=event_id,
                session_id=prot_ctx.session_id,
                task_id=prot_ctx.task_id,
            )

    def _process_submission(
        self,
        command: str,
        context: ProtectedContext,
        session_state: Optional[SessionState],
        mode: ExecutionMode,
        event_id: Optional[str],
        timestamp: str,
    ) -> ProtectedResponse:

        # ----------------------------------------------------
        # STEP 1: Workspace Boundary & Scope Validation
        # ----------------------------------------------------
        scope_ok, scope_reasons = self.gateway.validate_command_scope(command, context)
        if not scope_ok:
            # Audit log boundary violation
            self.audit_logger.log(
                command=command,
                v03_risk="HIGH_RISK",
                risk_score=90,
                capabilities=["DELETE_FILESYSTEM", "SYSTEM_CONFIGURATION"],
                final_policy_decision="BLOCK",
                policy_reasons=scope_reasons,
                event_id=event_id,
                session_id=context.session_id,
                task_id=context.task_id,
                approval_status="NOT_AVAILABLE",
            )
            return ProtectedResponse(
                gateway_status=GatewayStatus.REJECTED_SCOPE,
                command=command,
                policy_decision="BLOCK",
                enforcement_status="BLOCKED",
                reasons=scope_reasons,
                explanation=scope_reasons[0] if scope_reasons else "Workspace scope boundary violation.",
                timestamp=timestamp,
                event_id=event_id,
                session_id=context.session_id,
                task_id=context.task_id,
            )

        # ----------------------------------------------------
        # STEP 2: Aegis Brain Pipeline Evaluation (V0.3 -> V0.5 -> V0.4 -> V0.6)
        # ----------------------------------------------------
        safety_ass = self.safety_analyzer.analyze(command, session_state=session_state)
        route_decision = self.model_router.route(command, safety_assessment=safety_ass, session_state=session_state)
        ai_ass = self.ai_supervisor.analyze(command, session_state=session_state, safety_assessment=safety_ass)
        policy_ass = self.policy_engine.evaluate(
            command=command,
            safety_assessment=safety_ass,
            supervisor_assessment=ai_ass,
            routing_decision=route_decision,
            session_state=session_state,
            event_id=event_id,
            session_id=context.session_id,
            task_id=context.task_id,
        )

        # ----------------------------------------------------
        # STEP 3: V0.7 Enforcement Gate Processing
        # ----------------------------------------------------
        gate_result = self.enforcement_gate.process(
            policy_assessment=policy_ass,
            execution_mode=mode,
            event_id=event_id,
            session_id=context.session_id,
            task_id=context.task_id,
        )

        executor: CommandExecutor = ExecutorFactory.get_executor(mode)
        final_enforcement = executor.execute(request=gate_result, gate_result=gate_result)

        pol_dec_str = policy_ass.decision.value if isinstance(policy_ass.decision, PolicyDecision) else str(policy_ass.decision)
        enf_status_val = final_enforcement.status.value if isinstance(final_enforcement.status, EnforcementStatus) else str(final_enforcement.status)
        reasons_list = [r.explanation for r in policy_ass.reasons]

        # ----------------------------------------------------
        # STEP 4: Determine Gateway Status & Response
        # ----------------------------------------------------
        if enf_status_val in (EnforcementStatus.ALLOWED.value, EnforcementStatus.SIMULATED.value):
            gw_status = GatewayStatus.PERMITTED
            exp = "Command permitted and executed through protected gateway."
        elif enf_status_val == EnforcementStatus.WAITING_FOR_APPROVAL.value:
            gw_status = GatewayStatus.PAUSED_FOR_APPROVAL
            exp = "Execution paused: command requires explicit human approval."
        elif enf_status_val == EnforcementStatus.BLOCKED.value:
            gw_status = GatewayStatus.REJECTED_POLICY
            exp = "Execution prohibited: command is blocked by Aegis security policy."
        elif enf_status_val in (EnforcementStatus.DENIED.value, "EXPIRED", "CANCELLED"):
            gw_status = GatewayStatus.REJECTED_POLICY
            exp = f"Execution prohibited: human approval request is {final_enforcement.approval_status or 'denied'}."
        else:
            gw_status = GatewayStatus.FAILED_GATEWAY
            exp = f"Gateway failure: enforcement status is {enf_status_val}."

        response = ProtectedResponse(
            gateway_status=gw_status,
            command=command,
            policy_decision=pol_dec_str,
            enforcement_status=enf_status_val,
            approval_id=policy_ass.approval_request_id or final_enforcement.approval_id,
            approval_status=final_enforcement.approval_status,
            execution_result=final_enforcement.command_result.to_dict() if final_enforcement.command_result else None,
            reasons=reasons_list,
            explanation=exp,
            timestamp=timestamp,
            event_id=event_id,
            session_id=context.session_id,
            task_id=context.task_id,
            enforcement_id=final_enforcement.enforcement_id,
        )

        return response
