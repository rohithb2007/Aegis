import os
import sys
import yaml
import argparse
from observer.watcher import SessionWatcher
from observer.events import AntigravityEvent
from supervisor.session import SessionTracker
from supervisor.context import ContextSnapshot
from safety.analyzer import SafetyAnalyzer
from safety.explain import SafetyExplainer
from ai_supervisor.supervisor import AISupervisor
from ai_supervisor.router import ModelRouter
from policy.engine import PolicyEngine
from policy.config import PolicyConfig
from policy.approval import ApprovalManager
from enforcement.gate import EnforcementGate
from enforcement.executor import ExecutorFactory
from enforcement.models import ExecutionMode
from protected.proxy import CommandProxy
from protected.models import ProtectedContext, WorkspaceBoundary
from protected.daemon import AegisGatewayDaemon, start_daemon_cli
from protected.profile_installer import ProfileInstaller
from protected.protection import ProtectionManager


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load Aegis YAML configuration."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[Aegis Warning] Failed to load config file: {e}")
    return {}


import urllib.request
import urllib.error
import json


def _call_gateway(port: int, path: str, method: str = "GET", payload: dict = None):
    """Sends an HTTP request to the running Aegis Gateway HTTP Service daemon.
    Returns (success, status_code, response_data).
    """
    url = f"http://127.0.0.1:{port}{path}"
    try:
        data_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            body = resp.read().decode("utf-8")
            return True, resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        return False, err.code, json.loads(body) if body else {}
    except Exception:
        return False, 0, {}


def main():
    parser = argparse.ArgumentParser(
        description="Aegis V1.0.0-rc1 — External AI Supervision Layer for Antigravity"
    )
    parser.add_argument("--config", default="config/config.yaml", help="Path to config.yaml")
    parser.add_argument("--start", action="store_true", help="Start Aegis Gateway Service")
    parser.add_argument("--protection-status", action="store_true", help="Display Aegis protection status")
    parser.add_argument("--protection-on", action="store_true", help="Turn Aegis protection ON (Human Control)")
    parser.add_argument("--protection-off", action="store_true", help="Turn Aegis protection OFF (Human Control)")
    parser.add_argument("--once", action="store_true", help="Run a single poll cycle and exit")
    parser.add_argument("--state", action="store_true", help="Display Session Context state snapshot")
    parser.add_argument("--safety", action="store_true", help="Display Deterministic Safety Analysis for latest command")
    parser.add_argument("--ai", action="store_true", help="Display AI Supervisor contextual analysis for latest command")
    parser.add_argument("--route", action="store_true", help="Display Intelligent Model Router decision for latest command")
    parser.add_argument("--policy", action="store_true", help="Display Policy Engine decision for latest command")
    parser.add_argument("--enforce", action="store_true", help="Display Enforcement Gate & Executor result for latest command")
    parser.add_argument("--execution-mode", choices=["SIMULATION", "CONTROLLED", "LIVE"], default="SIMULATION", help="Enforcement execution mode (default: SIMULATION)")
    parser.add_argument("--approval-status", action="store_true", help="Display human approval manager state summary")
    parser.add_argument("--approval-list", action="store_true", help="List human approval requests")
    parser.add_argument("--approve", metavar="REQUEST_ID", help="Approve a pending human approval request")
    parser.add_argument("--deny", metavar="REQUEST_ID", help="Deny a pending human approval request")
    parser.add_argument("--enforcement-status", action="store_true", help="Display Aegis Enforcement Gate status summary")
    parser.add_argument("--protected-status", action="store_true", help="Display Aegis Protected Workspace Proxy status")
    parser.add_argument("--proxy-submit", metavar="COMMAND", help="Submit a command through Aegis CommandProxy before execution")
    parser.add_argument("--start-gateway", action="store_true", help="Start Aegis V0.9 Gateway HTTP Service")
    parser.add_argument("--install-interceptor", action="store_true", help="Install Aegis PowerShell profile pre-execution interceptor")
    parser.add_argument("--uninstall-interceptor", action="store_true", help="Remove Aegis PowerShell profile pre-execution interceptor")
    parser.add_argument("--interceptor-status", action="store_true", help="Check if PowerShell profile interceptor is active")
    parser.add_argument("--dashboard", action="store_true", help="Launch Aegis V1.1 Premium Security Operations Center Dashboard")
    parser.add_argument("--port", type=int, default=8765, help="Port for Aegis Gateway HTTP Service (default: 8765)")


    args = parser.parse_args()

    config = load_config(args.config)
    protection_manager = ProtectionManager()
    policy_config = PolicyConfig.from_env_or_dict(config.get("policy"))
    approval_manager = ApprovalManager()
    policy_engine = PolicyEngine(config=policy_config, approval_manager=approval_manager)

    exec_mode = ExecutionMode(args.execution_mode)
    gate = EnforcementGate(approval_manager=approval_manager, default_mode=exec_mode)
    executor = ExecutorFactory.get_executor(exec_mode)
    proxy = CommandProxy(policy_engine=policy_engine, approval_manager=approval_manager, protection_manager=protection_manager, default_mode=exec_mode)

    # Handle Protection CLI actions
    if args.protection_status:
        prot_dict = protection_manager.get_status_dict()
        interceptor_active = ProfileInstaller.is_installed()
        ok, status_code, data = _call_gateway(port=args.port, path="/status", method="GET")
        gw_status = "RUNNING" if ok else "OFFLINE"
        print("+====================================+")
        print("|      AEGIS PROTECTION STATUS       |")
        print("+====================================+")
        print(f"Protection State: {prot_dict['status']}")
        print(f"Interceptor:      {'ACTIVE' if interceptor_active else 'INACTIVE'}")
        print(f"Gateway Service:  {gw_status} (port {args.port})")
        print(f"Updated At:       {prot_dict.get('updated_at') or 'N/A'}")
        print(f"Updated By:       {prot_dict.get('updated_by') or 'DEFAULT'}")
        print("+====================================+")
        return

    if args.protection_on:
        protection_manager.set_protection(True, source="HUMAN_CLI")
        _call_gateway(port=args.port, path="/protection", method="POST", payload={"state": "ON"})
        print("[Aegis Protection] Protection state updated to: ON")
        print("[Aegis Notice] Aegis supervision enabled. Gateway unavailable => FAIL CLOSED.")
        return

    if args.protection_off:
        if os.environ.get("ANTIGRAVITY_AGENT") or os.environ.get("ANTIGRAVITY_TRAJECTORY_ID"):
            print("[Aegis Security Error] Antigravity agent is strictly prohibited from disabling Aegis protection.")
            sys.exit(1)
        protection_manager.set_protection(False, source="HUMAN_CLI")
        _call_gateway(port=args.port, path="/protection", method="POST", payload={"state": "OFF"})
        print("[Aegis Protection] Protection state updated to: OFF")
        print("[Aegis Warning] Aegis protection has been intentionally disabled by human choice.")
        return

    if args.start or args.start_gateway:
        start_daemon_cli(port=args.port)
        return

    if args.dashboard:
        print("[Aegis SOC] Aegis V1.1 Premium Security Operations Center Dashboard")
        dashboard_dir = os.path.join(os.path.dirname(__file__), "dashboard")
        if os.path.exists(dashboard_dir):
            import subprocess
            ok, _, _ = _call_gateway(port=args.port, path="/status", method="GET")
            if not ok:
                print(f"[Aegis SOC] Note: Aegis Gateway Service is currently OFFLINE. Run 'python main.py --start' to enable real-time backend synchronization.")
            print("[Aegis SOC] Launching Dashboard interface on http://localhost:5173 ...")
            subprocess.run(["npm", "run", "dev"], cwd=dashboard_dir, shell=True)
        else:
            print("[Aegis SOC Error] Dashboard directory not found.")
        return


    # Handle Approval CLI actions first if specified (communicating with Gateway)
    if args.approve:
        ok, status_code, data = _call_gateway(port=args.port, path="/approve", method="POST", payload={"request_id": args.approve})
        if ok and status_code == 200:
            print(f"[Aegis Approval] Request '{args.approve}' set to APPROVED via Aegis Gateway.")
            print("[Aegis Notice] Approval updates internal Aegis state. Action is now cleared for enforcement.")
        elif status_code == 404:
            print(f"[Aegis Approval Error] Request '{args.approve}' not found or not in PENDING status.")
            sys.exit(1)
        else:
            print(f"[Aegis Approval Error] Aegis Gateway unavailable on port {args.port}.\nApproval action was NOT performed.\nStart the gateway and retry.")
            sys.exit(1)
        return

    if args.deny:
        ok, status_code, data = _call_gateway(port=args.port, path="/deny", method="POST", payload={"request_id": args.deny})
        if ok and status_code == 200:
            print(f"[Aegis Approval] Request '{args.deny}' set to DENIED via Aegis Gateway.")
            print("[Aegis Notice] Request denied. Enforcement gate will prohibit execution.")
        elif status_code == 404:
            print(f"[Aegis Approval Error] Request '{args.deny}' not found or not in PENDING status.")
            sys.exit(1)
        else:
            print(f"[Aegis Approval Error] Aegis Gateway unavailable on port {args.port}.\nApproval action was NOT performed.\nStart the gateway and retry.")
            sys.exit(1)
        return

    if args.approval_status:
        ok, status_code, data = _call_gateway(port=args.port, path="/requests", method="GET")
        if not ok:
            print(f"[Aegis Approval Error] Aegis Gateway unavailable on port {args.port}.\nStart the gateway and retry.")
            sys.exit(1)
        
        reqs = data.get("requests", [])
        pending_count = len([r for r in reqs if r.get("status") == "PENDING"])
        approved_count = len([r for r in reqs if r.get("status") == "APPROVED"])
        denied_count = len([r for r in reqs if r.get("status") == "DENIED"])
        print("+====================================+")
        print("|    AEGIS APPROVAL MANAGER STATE    |")
        print("+====================================+")
        print(f"Total Requests:   {len(reqs)}")
        print(f"Pending:          {pending_count}")
        print(f"Approved:         {approved_count}")
        print(f"Denied:           {denied_count}")
        print("Gateway Service:  CONNECTED")
        print("+====================================+")
        return

    if args.approval_list:
        ok, status_code, data = _call_gateway(port=args.port, path="/requests", method="GET")
        if not ok:
            print(f"[Aegis Approval Error] Aegis Gateway unavailable on port {args.port}.\nStart the gateway and retry.")
            sys.exit(1)

        reqs = data.get("requests", [])
        print("+====================================+")
        print("|     AEGIS APPROVAL REQUESTS        |")
        print("+====================================+")
        if not reqs:
            print("No approval requests currently tracked.")
        else:
            for r in reqs:
                cmd = r.get("command", "")[:40]
                st = r.get("status", "UNKNOWN")
                risk = r.get("risk_classification", "UNKNOWN")
                rid = r.get("request_id", "")
                print(f"ID: {rid} | Status: {st} | Cmd: {cmd} | Risk: {risk}")
        print("+====================================+")
        return

    if args.enforcement_status:
        print("+====================================+")
        print("|    AEGIS ENFORCEMENT GATE STATUS   |")
        print("+====================================+")
        print(f"Execution Mode:   {exec_mode.value}")
        print("Integration:      Read-Only Session Ingestion (Pre-Execution Hook: Advisory)")
        print("Gate Engine:      V0.7 Active")
        print("+====================================+")
        return

    if args.protected_status:
        interceptor_active = ProfileInstaller.is_installed()
        print("+====================================+")
        print("|  AEGIS PROTECTED WORKSPACE PROXY   |")
        print("+====================================+")
        print(f"Workspace Root:   {proxy.boundary.workspace_root}")
        print(f"Strict Boundary:  {proxy.boundary.strict_scope_check}")
        print(f"Execution Mode:   {exec_mode.value}")
        print("Proxy Engine:     V0.9 Active")
        print(f"Interceptor:      {'ACTIVE' if interceptor_active else 'NOT INSTALLED'}")
        print("+====================================+")
        return

    if args.start_gateway:
        start_daemon_cli(port=args.port)
        return

    if args.install_interceptor:
        ok, msg = ProfileInstaller.install()
        if ok:
            print(f"[Aegis Interceptor] SUCCESS: {msg}")
        else:
            print(f"[Aegis Interceptor] ERROR: {msg}")
        return

    if args.uninstall_interceptor:
        ok, msg = ProfileInstaller.uninstall()
        if ok:
            print(f"[Aegis Interceptor] SUCCESS: {msg}")
        else:
            print(f"[Aegis Interceptor] ERROR: {msg}")
        return

    if args.interceptor_status:
        active = ProfileInstaller.is_installed()
        path = ProfileInstaller.get_profile_path()
        print("+====================================+")
        print("|  AEGIS POWERSHELL INTERCEPTOR      |")
        print("+====================================+")
        print(f"Profile Path:     {path}")
        print(f"Status:           {'ACTIVE' if active else 'INACTIVE'}")
        print("+====================================+")
        return

    if args.proxy_submit:
        res = proxy.submit(args.proxy_submit, execution_mode=exec_mode)
        print("\n" + res.render_console())
        return

    base_dir = config.get("antigravity", {}).get("base_dir") or None
    poll_interval = config.get("observer", {}).get("poll_interval_seconds", 1.0)

    try:
        watcher = SessionWatcher(base_dir=base_dir, poll_interval=poll_interval)
    except FileNotFoundError as err:
        print(f"[Aegis Error] {err}")
        sys.exit(1)

    tracker = SessionTracker()
    analyzer = SafetyAnalyzer()
    ai_sup = AISupervisor()
    router = ModelRouter(config=config.get("router"))

    def on_event(event: AntigravityEvent):
        tracker.process_event(event)
        if not args.state and not args.safety and not args.ai and not args.route and not args.policy and not args.enforce:
            formatted = event.to_console_str()
            if formatted:
                print(f"\n{formatted}")

    watcher.add_callback(on_event)

    if args.once:
        print("[Aegis] Starting observer, safety, router, AI supervisor, policy, enforcement & protected proxy (single run)...")
        print(f"[Aegis] Antigravity directory detected: {watcher.base_dir}")
        watcher.poll_once()

        if args.state:
            print("\n" + ContextSnapshot.render_console(tracker.state))

        last_cmd = tracker.state.commands[-1].command if tracker.state.commands else "git status"
        assessment = analyzer.analyze(last_cmd, session_state=tracker.state)

        if args.safety:
            print("\n" + SafetyExplainer.render_console(assessment))

        routing_decision = None
        if args.route or args.policy or args.enforce:
            routing_decision = router.route(last_cmd, safety_assessment=assessment, session_state=tracker.state)
            if args.route:
                print("\n" + routing_decision.render_console())

        ai_assessment = None
        if args.ai or args.policy or args.enforce:
            ai_assessment = ai_sup.analyze(last_cmd, session_state=tracker.state, safety_assessment=assessment)
            if args.ai:
                print("\n" + AISupervisor.render_console(ai_assessment))

        policy_assessment = None
        if args.policy or args.enforce:
            policy_assessment = policy_engine.evaluate(
                command=last_cmd,
                safety_assessment=assessment,
                supervisor_assessment=ai_assessment,
                routing_decision=routing_decision,
                session_state=tracker.state,
            )
            if args.policy:
                print("\n" + policy_assessment.render_console())

        if args.enforce:
            if not policy_assessment:
                policy_assessment = policy_engine.evaluate(
                    command=last_cmd,
                    safety_assessment=assessment,
                    supervisor_assessment=ai_assessment,
                    routing_decision=routing_decision,
                    session_state=tracker.state,
                )
            gate_res = gate.process(policy_assessment, execution_mode=exec_mode)
            final_res = executor.execute(request=gate_res, gate_result=gate_res)
            print("\n" + final_res.render_console())

        print("\n[Aegis] Poll completed.")
    else:
        watcher.start()


if __name__ == "__main__":
    main()
