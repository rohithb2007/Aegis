# Changelog

All notable changes to Aegis will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-10-03

### Added
- **Premium SOC Dashboard:** Modern Security Operations Center web UI built with React 19, TypeScript, Vite, and Lucide icons.
- **Dual Visual Themes:** Dark Obsidian (sleek glassmorphism) and Warm Off-White/Brown themes.
- **Human Approval Center:** Dedicated management page displaying pending approval requests with full explainability breakdown and single-click `APPROVE` or `DENY` authorization.
- **Security Audit Explorer:** Real-time secret-redacted audit log viewer with filtering by status (`ALLOW`, `REVIEW`, `BLOCK`) and risk level.
- **Protection Toggle Interface:** Human-only protection state control with CORS-restricted REST endpoints.

### Fixed & Hardened
- **Approval-State Audit Accuracy:** Fixed audit logger timing in `PolicyEngine.evaluate` so that evaluations matching pre-approved requests log `final_policy_decision: "PERMITTED"` and `approval_status: "APPROVED"` rather than `REVIEW` / `PENDING`.
- **CORS Hardening:** Restricted Gateway HTTP CORS headers strictly to explicit localhost origins (`http://localhost:5173`, `http://127.0.0.1:5173`).
- **Fail-Closed Reliability:** Reinforced fail-closed fallback behavior across Gateway HTTP timeouts and daemon shutdown.
- **Test Suite Expansion:** Full test suite expanded to **242 passing tests** with 100% offline execution.

---

## [1.0.0] - 2026-09-15

### Added
- Initial V1.0 core release featuring observer pipeline, safety analyzer, AI supervisor, intelligent model router, policy engine, enforcement gate, and protected workspace proxy.
