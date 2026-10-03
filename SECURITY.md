# Aegis Security Policy

## Overview & Security Model

Aegis is an external, local security supervision layer designed to observe AI coding-agent activity, evaluate proposed command safety and context alignment, enforce granular policy decisions, and require explicit human approval for high-risk operations.

Aegis operates on an authoritative fail-closed local Gateway architecture (`127.0.0.1:8765`).

---

## Security Invariants

1. **Fail-Closed Execution Boundary:** When Aegis Protection is `ON`, if the Gateway service is offline, unreachable, or encounters an internal evaluation error, proposed execution is automatically **BLOCKED** (`Exit 3` / `FAILED_GATEWAY`).
2. **Human-Only Protection Toggles:** Protection state (`ON` / `OFF`) can only be modified via explicit human CLI / management interface. AI coding-agent contexts (e.g. `ANTIGRAVITY_AGENT` or `ANTIGRAVITY_TRAJECTORY_ID`) are strictly prohibited from disabling protection (HTTP 403 Forbidden).
3. **Non-Overridable Critical Invariants:** Critical destructive actions (such as `rm -rf /` or system directory deletions) evaluate to `BLOCK`. Human approval cannot downgrade or override `CRITICAL` policy blocks.
4. **Exact-Command Approval Binding:** Approvals granted by human decision are strictly bound to the exact normalized command string (`normalize_command`) and session/task/workspace context. Changing command arguments or flags invalidates previous approval.
5. **Secret Redaction:** API keys, access tokens, credentials, and private keys are automatically redacted (`[REDACTED_SECRET_KEY]`) prior to structured logging, IPC transmission, or telemetry rendering.
6. **Localhost Isolation:** The Aegis Gateway and SOC Dashboard operate exclusively on `127.0.0.1`. CORS is strictly restricted to local development origins (`http://localhost:5173`, `http://127.0.0.1:5173`). No external cloud endpoints or remote tracking services are invoked.

---

## Verified Interception Boundaries & Limitations

Aegis explicitly documents its verified execution boundaries:

- **Verified Interception:** Interception of line-by-line tool executions matching the verified Antigravity PowerShell profile boundary (`Invoke-AegisPreExecutionBoundary`).
- **PowerShell `-NoProfile` Boundary:** Direct execution of `powershell.exe -NoProfile` bypasses profile-based pre-execution hooks.
- **Interactive Shell REPL:** Persistent interactive subshell REPL sessions operate after shell startup; commands entered inside an existing subshell REPL are outside the line-by-line profile startup boundary.
- **Direct Kernel / Native Execution:** Aegis does not implement kernel-level driver or eBPF process hooking. Native processes spawned directly outside the verified shell profile boundary are not intercepted.

---

## Reporting a Security Vulnerability

If you discover a potential security flaw or bypass in Aegis, please report it responsibly:

- **Email:** Open an issue marked `[SECURITY DISCLOSURE]` or contact the maintainers directly.
- **Details:** Include a clear reproduction command, environment details, and expected vs observed enforcement behavior.
- **Response:** We aim to acknowledge security reports within 48 hours and provide a patch/mitigation promptly.
