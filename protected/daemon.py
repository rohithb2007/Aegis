import os
import sys
import json
import logging
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
from protected.proxy import CommandProxy
from protected.models import ProtectedContext
from protected.protection import ProtectionManager
from enforcement.models import ExecutionMode
from policy.approval import ApprovalManager
from policy.engine import PolicyEngine
from policy.config import PolicyConfig
from policy.audit import AuditLogger

logger = logging.getLogger("AegisDaemon")


class AegisGatewayDaemon:
    """Aegis V0.9.3 Local Gateway HTTP/IPC Daemon Service."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        proxy: Optional[CommandProxy] = None,
        protection_manager: Optional[ProtectionManager] = None,
        execution_mode: ExecutionMode = ExecutionMode.SIMULATION,
    ):
        self.host = host
        self.port = port
        self.protection_manager = protection_manager or ProtectionManager()
        self.approval_manager = ApprovalManager()
        self.audit_logger = AuditLogger()
        self.policy_config = PolicyConfig.from_env_or_dict()
        self.policy_engine = PolicyEngine(
            config=self.policy_config,
            approval_manager=self.approval_manager,
            audit_logger=self.audit_logger,
        )
        self.proxy = proxy or CommandProxy(
            policy_engine=self.policy_engine,
            approval_manager=self.approval_manager,
            audit_logger=self.audit_logger,
            protection_manager=self.protection_manager,
            default_mode=execution_mode,
        )
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.total_evaluated = 0

    def start_in_background(self):
        """Start daemon server in a background thread."""
        daemon_self = self
        ALLOWED_ORIGINS = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        }

        class GatewayRequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress default HTTP logging to stdout

            def _get_request_origin(self) -> Optional[str]:
                orig = self.headers.get("Origin") or self.headers.get("origin")
                return orig.rstrip("/") if orig else None

            def _apply_cors_headers(self):
                origin = self._get_request_origin()
                if origin and origin in ALLOWED_ORIGINS:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                    self.send_header("Vary", "Origin")

            def _send_json(self, status_code: int, data: Dict[str, Any]):
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self._apply_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))

            def do_OPTIONS(self):
                origin = self._get_request_origin()
                if origin and origin not in ALLOWED_ORIGINS:
                    self.send_response(403)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "CORS policy prohibited origin"}).encode("utf-8"))
                    return

                self.send_response(204)
                self._apply_cors_headers()
                self.end_headers()

            def do_GET(self):
                try:
                    parsed_url = urlparse(self.path)
                    clean_path = parsed_url.path
                    query_params = parse_qs(parsed_url.query)

                    if clean_path in ("/status", "/"):
                        reqs = daemon_self.approval_manager.list_requests()
                        pending = len([r for r in reqs if (r.status.value if hasattr(r.status, "value") else str(r.status)) == "PENDING"])
                        prot_on = daemon_self.protection_manager.is_protection_on()
                        self._send_json(
                            200,
                            {
                                "status": "RUNNING",
                                "version": "V1.1.0",
                                "port": daemon_self.port,
                                "protection_status": "ON" if prot_on else "OFF",
                                "protection_enabled": prot_on,
                                "workspace_root": daemon_self.proxy.boundary.workspace_root,
                                "total_evaluated": daemon_self.total_evaluated,
                                "pending_approvals": pending,
                            },
                        )
                    elif clean_path in ("/requests", "/approval/requests"):
                        reqs = daemon_self.approval_manager.list_requests()
                        self._send_json(200, {"requests": [r.to_dict() for r in reqs]})
                    elif clean_path in ("/protection", "/protection/status"):
                        stat = daemon_self.protection_manager.get_status_dict()
                        self._send_json(200, stat)
                    elif clean_path in ("/audit/recent", "/audit/logs", "/audit"):
                        limit_val = 50
                        if "limit" in query_params:
                            try:
                                limit_val = int(query_params["limit"][0])
                            except Exception:
                                limit_val = 50
                        logs = daemon_self.audit_logger.read_recent(limit=limit_val)
                        self._send_json(200, {"recent_logs": logs})
                    elif clean_path == "/tasks":
                        reqs = daemon_self.approval_manager.list_requests()
                        tasks = {}
                        for r in reqs:
                            t_id = r.task_id or "default_task"
                            st_val = r.status.value if hasattr(r.status, "value") else str(r.status)
                            if st_val == "PENDING":
                                task_st = "WAITING_FOR_APPROVAL"
                            elif st_val == "APPROVED":
                                task_st = "RUNNING"
                            elif st_val in ("DENIED", "EXPIRED", "CANCELLED"):
                                task_st = "BLOCKED"
                            else:
                                task_st = "RUNNING"
                            tasks[t_id] = {
                                "task_id": t_id,
                                "status": task_st,
                                "last_command": r.command,
                                "request_id": r.request_id,
                            }
                        self._send_json(200, {"tasks": list(tasks.values())})
                    else:
                        self._send_json(404, {"error": "Not Found"})
                except Exception as err:
                    logger.error(f"[Gateway HTTP Exception] do_GET error: {err}")
                    self._send_json(500, {"error": "Internal Gateway Error", "gateway_status": "FAILED_GATEWAY", "policy_decision": "BLOCK"})

            def do_POST(self):
                try:
                    parsed_url = urlparse(self.path)
                    clean_path = parsed_url.path

                    content_len = int(self.headers.get("Content-Length", 0))
                    if content_len > 10 * 1024 * 1024:  # 10MB limit
                        self._send_json(413, {"error": "Payload Too Large"})
                        return
                    body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"
                    try:
                        payload = json.loads(body_bytes.decode("utf-8"))
                        if not isinstance(payload, dict):
                            payload = {}
                    except Exception:
                        payload = {}

                    if clean_path == "/evaluate":
                        cmd = payload.get("command", "")
                        cwd = payload.get("cwd") or os.getcwd()
                        workspace_root = payload.get("workspace_root") or daemon_self.proxy.boundary.workspace_root
                        session_id = payload.get("session_id")
                        task_id = payload.get("task_id")

                        ctx = ProtectedContext(
                            workspace_root=workspace_root,
                            cwd=cwd,
                            session_id=session_id,
                            task_id=task_id,
                        )

                        res = daemon_self.proxy.submit(command=cmd, context=ctx)
                        daemon_self.total_evaluated += 1

                        resp_data = {
                            "gateway_status": res.gateway_status.value if hasattr(res.gateway_status, "value") else str(res.gateway_status),
                            "policy_decision": res.policy_decision,
                            "enforcement_status": res.enforcement_status,
                            "approval_id": res.approval_id,
                            "approval_status": res.approval_status,
                            "reasons": res.reasons,
                            "explanation": res.explanation,
                            "command": res.command,
                            "session_id": res.session_id,
                            "task_id": res.task_id,
                        }

                        # Structured Aegis Telemetry (with secret redaction)
                        sanitized_cmd = daemon_self.audit_logger.sanitizer.redact_secrets(cmd or "")
                        dec = res.policy_decision or "UNKNOWN"
                        gw_st = resp_data["gateway_status"]
                        print(f"[AEGIS TELEMETRY] EVALUATE | cmd='{sanitized_cmd}' | decision={dec} | status={gw_st} | session={session_id or 'none'} | task={task_id or 'none'}", flush=True)
                        if res.approval_id:
                            print(f"[AEGIS TELEMETRY]   -> approval_id={res.approval_id}", flush=True)
                        if res.explanation:
                            sanitized_exp = daemon_self.audit_logger.sanitizer.redact_secrets(res.explanation)
                            print(f"[AEGIS TELEMETRY]   -> explanation='{sanitized_exp}'", flush=True)

                        if res.gateway_status.value in ("PERMITTED", "PASSTHROUGH"):
                            status_code = 200
                        elif res.gateway_status.value == "PAUSED_FOR_APPROVAL":
                            status_code = 202
                        else:
                            status_code = 403

                        self._send_json(status_code, resp_data)

                    elif clean_path == "/approve":
                        req_id = payload.get("request_id")
                        if not req_id:
                            self._send_json(400, {"error": "Missing request_id"})
                            return
                        req = daemon_self.approval_manager.approve(req_id)
                        req_st = (req.status.value if hasattr(req.status, "value") else str(req.status)) if req else None
                        if req and req_st == "APPROVED":
                            sanitized_cmd = daemon_self.audit_logger.sanitizer.redact_secrets(req.command)
                            print(f"[AEGIS TELEMETRY] APPROVAL | request_id={req_id} | status=APPROVED | command='{sanitized_cmd}'", flush=True)
                            self._send_json(200, {"status": "APPROVED", "request_id": req_id})
                        else:
                            self._send_json(404, {"error": f"Request '{req_id}' not found or not PENDING"})

                    elif clean_path == "/deny":
                        req_id = payload.get("request_id")
                        if not req_id:
                            self._send_json(400, {"error": "Missing request_id"})
                            return
                        req = daemon_self.approval_manager.deny(req_id)
                        req_st = (req.status.value if hasattr(req.status, "value") else str(req.status)) if req else None
                        if req and req_st == "DENIED":
                            sanitized_cmd = daemon_self.audit_logger.sanitizer.redact_secrets(req.command)
                            print(f"[AEGIS TELEMETRY] DENIAL | request_id={req_id} | status=DENIED | command='{sanitized_cmd}'", flush=True)
                            self._send_json(200, {"status": "DENIED", "request_id": req_id})
                        else:
                            self._send_json(404, {"error": f"Request '{req_id}' not found or not PENDING"})

                    elif clean_path in ("/protection", "/protection/set"):
                        # Check if request attempts to come from agent command context
                        if payload.get("session_id") or payload.get("task_id") or payload.get("source") == "agent":
                            self._send_json(403, {"error": "Antigravity agent cannot alter Aegis protection state."})
                            return

                        target_state = str(payload.get("state") or payload.get("status") or "").upper()
                        if target_state in ("ON", "ENABLE", "TRUE"):
                            stat = daemon_self.protection_manager.set_protection(True, source="HUMAN_MANAGEMENT_API")
                            self._send_json(200, {"status": "ON", "details": stat})
                        elif target_state in ("OFF", "DISABLE", "FALSE"):
                            stat = daemon_self.protection_manager.set_protection(False, source="HUMAN_MANAGEMENT_API")
                            self._send_json(200, {"status": "OFF", "details": stat})
                        else:
                            self._send_json(400, {"error": "Invalid state. Must be 'ON' or 'OFF'."})

                    elif clean_path == "/shutdown":
                        self._send_json(200, {"status": "SHUTTING_DOWN"})
                        threading.Thread(target=daemon_self.stop).start()
                    else:
                        self._send_json(404, {"error": "Not Found"})
                except Exception as err:
                    logger.error(f"[Gateway HTTP Exception] do_POST error: {err}")
                    self._send_json(500, {"error": "Internal Gateway Error", "gateway_status": "FAILED_GATEWAY", "policy_decision": "BLOCK"})

            def do_PUT(self):
                self._send_json(405, {"error": "Method Not Allowed"})

            def do_DELETE(self):
                self._send_json(405, {"error": "Method Not Allowed"})

        self.server = ThreadingHTTPServer((self.host, self.port), GatewayRequestHandler)
        self.server.daemon_threads = True
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        logger.info(f"[Aegis Daemon] Started Gateway Service on http://{self.host}:{self.port}")

    def stop(self):
        if self.server:
            srv = self.server
            self.server = None
            srv.shutdown()
            srv.server_close()
            logger.info("[Aegis Daemon] Stopped Gateway Service.")


def start_daemon_cli(port: int = 8765):
    daemon = AegisGatewayDaemon(port=port)
    daemon.start_in_background()
    print("AEGIS")
    print("Protection: ON")
    print("Gateway: RUNNING")
    print(f"Listening: 127.0.0.1:{port}")
    try:
        while daemon.server:
            threading.Event().wait(1.0)
    except KeyboardInterrupt:
        print("\n[Aegis Gateway Service] Stopping...")
        daemon.stop()


if __name__ == "__main__":
    start_daemon_cli()
