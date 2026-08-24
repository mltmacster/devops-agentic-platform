# =============================================
# 🏛️ VAULT ARCHITECTURE OVERVIEW
# =============================================

## Project: DevOps Agentic Platform (DAP)
**Repository Root**: `/devops-agentic-platform/`

---

## Current Architecture State

```
┌───────────────────────┐     ┌──────────────────┐
│    Client Layer       │     │  Edge & Gateway   │
│ Browser / VS Code Ext│────▶│ WAF + API GW     │
└───────────────────────┘     └────────┬─────────┘
                                      │
                    ┌───────────────▼───────────────┐
                    │  Control Plane (FastAPI)      │
                    ├───────────────┬───────────────┤
                    │ Auth Service  │ Workspace     │
                    │ (IAM/RBAC)    │ Orchestrator  │
                    ├───────────────┤ Sandbox LM    │
                    │ Observability │ Agentic AI    │
                    │ Collector     │ Engine        │
                    │ Network Edge  │ IDE Core      │
                    └───────────────┴───────────────┘
                                      │
                    ┌───────────────▼───────────────┐
                    │  Data Plane (Shared Services)   │
                    ├───────────────┬───────────────┤
                    │ Lite VM Pool  │ Redis Cluster   │
                    │ (Ubuntu 24.04)│ PostgreSQL +    │
                    └───────────────┤ pgVector 0.8.0   │
```

## Service Status Matrix

| Service | Files | Tests | Status | Last Updated |
|---------|-------|-------|--------|-------------|
| Auth | `src/api/auth/` (3 files) | 13 ✅ | Active | 2026-08-21 |
| Workspace | `src/api/workspace/` (1 file) | 11 ✅ | Active | 2026-08-21 |
| Sandbox | `src/api/sandbox/` (1 file) | 11 ⚠️ | Active | 2026-08-21 |
| IDE Core (Phase 2) | `src/api/ide/` (1 file) | **11 ✅** | **Active** | 2026-08-21 |
| Observability (Phase 2) | `src/api/observability/` (1 file; dead collector archived) | **30 ✅** | **Active** | 2026-08-23 |
| Agentic AI (Phase 3) | `src/agentic/` (6 + common/ 2) + `src/api/agentic/` (1) | **24 ✅** | **Active** | 2026-08-23 |
| Network (Phase 5) | `src/network/` (4 files) | **20 ✅** | **Active** | 2026-08-23 |

## Phase 2 — IDE Integration & Observability (COMPLETE) ✅

### IDE Core (`src/api/ide/`)
- **WebSocket endpoint** `/ws/{session_id}` — Monaco Editor ↔ DAP real-time communication
- **LSP protocol** support for textDocument operations:
  - `didOpen`, `didChange`, `didSave`, `saveAll` (event push)
  - `completion`, `hover`, `definition`, `references`, `codeActions` (request/response)
- **REST endpoints**: `/config`, `/config/current`, `/lsp/capabilities`, `/lsp/info`
- **Health probes**: `/health/live`, `/health/ready`

### Observability Collector (`src/api/observability/`)
- **Prometheus exporter** `/metrics` — text/plain with:
  - `dap_ide_active_sessions`, `dap_workspace_total`, `dap_sandbox_running_number_of_sandboxes`
  - `dap_ai_tokens_total`, `dap_api_requests_total` (counters)
  - `dap_memory_usage_bytes`, `dap_cpu_usage_percent`, `dap_disk_free_bytes` (gauges)
  - `dap_ai_latency_seconds_bucket` (histogram with latency percentiles)
- **Grafana integration**:
  - `/grafana/dashboard` — Importable v12.4+ JSON dashboard (3 rows, 10 panels)
  - `/grafana/datasource` — Prometheus datasource config for Grafana import
- **Health endpoints**: `/health`, `/health/live`, `/health/ready`
- **JSON summary**: `/metrics/summary`

---

## Phase 3 — Agentic AI Engine (COMPLETE) ✅

### Agents (`src/agentic/`)
- `CodeArchitectAgent` — classifies project type, scaffolds 6 project types
- `DebuggerAgent` — 12 error types via phrase matching
- `TestGeneratorAgent` — unit + integration test generation
- `AgenticAIOrchestrator` — intent classification (debug → test → architect) + routing

### Agentic API (`src/api/agentic/`)
- `POST /api/agentic/run` — {sandbox_id, query} → agent-routed result
- `GET /api/agentic/health/live` / `ready`
- Backends are currently heuristic/keyword-based; real LLM backend is a known TODO (see `HANDOFF.md`)

---

## Phase 5 — Networkability & Production Readiness (COMPLETE) ✅

### Network Edge (`src/network/`)
- `public_routing.py` — `PublicEndpointRouter`: sandbox registration/deregistration (in-memory)
- `dns_config.py` — `DNSConfigManager`: A/CNAME/SRV/MX records + BIND zone-file export
- `ssl_manager.py` — `CertificateManager`: self-signed (dev) + CA-signed certs
- `url_formatter.py` — `NetworkConfig`, `build_ide_url()`, sandbox response URL formatting (Phase 1)
- 10 endpoints under `/api/network/` (registered in `src/main.py`)

---

## Open Decisions / TODOs

1. **IDE Integration** — ✅ Done: WebSocket server for Monaco Editor + LSP
2. **Observability** — ✅ Done: Prometheus metrics collection and Grafana Dashboard API  
3. **Auth Persistence** — Still stubbed; needs real user storage (DB or identity provider)
4. **RBAC Testing** — Need integration tests for actual role-based access
5. **Agentic AI Engine** — ✅ Done (Phase 3); real LLM backend replaces heuristics (see `HANDOFF.md`)
6. **Networkability** — ✅ Done (Phase 5); production would use NGINX/ALB + Let's Encrypt
7. **Git repository** — ✅ Initialized 2026-08-23 (local `main`, no remote); add a GitHub remote to activate the CI workflow

## Future Considerations (Noted)

> **URL formatting & networkability**: The IDE WebSocket endpoint needs proper URL routing/networkability for production deployment. Both the IDE and Observability services should run in parallel to provide resilience — if one degrades, the other remains available. This dual-process architecture was intentional and should be preserved.

## Vault Location
`.vault/` — Project's persistent knowledge repository (protected from agent deletion)
