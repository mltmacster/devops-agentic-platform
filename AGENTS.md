# =============================================
# DevOps Agentic Development Platform (DAP) — VAULT INTEGRATION
# =============================================

**VAULT RULES**: The `.vault/` directory is the project's permanent knowledge repository.

## 🏛️ VAULT: Non-Removable Knowledge Repository

The `.vault/` directory is the project's official knowledge repository. It persists across sessions and is protected from agent deletion or modification.

### What Lives in `.vault/`
- **Snapshots**: UI/code state at key moments (for preview & regression testing)
- **Solutions**: Documented troubleshooting with root cause analysis  
- **Designs**: Architecture diagrams, ADRs, Mermaid diagrams
- **Scripts**: Reusable debugging & automation scripts
- **Docs**: Technical documentation, API references
- **Metrics**: Performance benchmarks & test reports
- **Archive**: Deprecated/retired components with lifecycle documentation

### Agent Behavior Rules (NON-NEGOTIABLE)
1. **NEVER delete files** in `.vault/` without explicit human approval
2. **ALWAYS create snapshots** before major code changes (> 50 lines)  
3. **Document all fixes** in `.vault/SOLUTIONS.md` with verification steps
4. **Never auto-purge** old content — nothing is automatically deleted
5. **All changes must be traced** back to a specific session/commit
6. **Vault schema files** (`VAULT_CONFIG.yaml`, `VAULT_COORDINATOR.yaml`,
   `VAULT_DEPLOYMENT.yaml`) may only be changed with explicit user approval,
   and every change must carry a **version header** noting what changed and why
   (the 2026-08-24 consistency pass set this precedent)

### Quick Commands
```bash
# Run all tests with SQLite backend
export TESTING=1 && python -m pytest tests/ -v   # TESTING=1 selects the SQLite backend (no PostgreSQL needed)

# Validate Vault configs
bash .vault/scripts/validate_vault.sh

# System health audit (or `cleanup` / `full` — see Compute Automation section)
bash .vault/scripts/run_computing.sh audit

# Add snapshot after major changes
mkdir -p .vault/snapshots/YYYY-MM-DD-HH/MM/<service>/
# Document changes in SNAPSHOT_LOG.md

# Archive deprecated component
mkdir -p .vault/archive/YYYY-MM-DD_<component>/
cp old-code/ .vault/archive/YYYY-MM-DD_<component>/
# Create RETIREMENT.md with migration path
```

### Repository Root
```
devops-agentic-platform/
├── .vault/                           # ← Knowledge repository (protected)
│   ├── VAULT_CONFIG.yaml               # Schema definitions (v1.1, READ-ONLY w/o approval)
│   ├── VAULT_COORDINATOR.yaml        # Coordination rules (v1.1, READ-ONLY w/o approval)
│   ├── VAULT_DEPLOYMENT.yaml         # Roadmap & pipeline (v2.0.0; v1 in archive/)
│   ├── LIFECYCLE_PROTOCOL.md         # Artifact lifecycle rules
│   ├── ARCHITECTURE.md               # Current architecture state (v1.1)
│   ├── VAULT_OVERVIEW.md             # Architecture overview + service matrix
│   ├── SNAPSHOT_LOG.md               # All snapshots tracked here
│   ├── SOLUTIONS.md                  # 33 documented solutions (28–33 = 2026-08-24)
│   ├── snapshots/                    # UI/code state at key moments
│   ├── designs/                      # Architecture diagrams, ADRs
│   ├── scripts/                      # run_computing.sh, run_all_tests.sh, validate_vault.sh
│   ├── docs/, metrics/               # Technical docs, benchmarks
│   ├── certs/, logs/                 # SSL certs, service logs
│   └── archive/                      # Retired components + RETIREMENT.md
├── src/                              # Source code
├── templates/                        # Infrastructure templates  
├── tests/                            # Test suite (219 tests, run with TESTING=1)
│   ├── test_auth_api.py              # legacy auth/RBAC tests ✅
│   ├── test_auth_users.py            # real user store: register/login/JWT/strict+dev ✅
│   ├── test_sandbox_api.py           # sandbox lifecycle tests ✅
│   ├── test_sandbox_engine.py        # sandbox engine + state machine tests ✅
│   ├── test_sandbox_backends.py      # null/Podman/gVisor backends + failure parking ✅
│   ├── test_workspace_api.py         # workspace CRUD + list tests ✅
│   ├── test_ide_api.py               # IDE config/LSP tests ✅
│   ├── test_observability_api.py     # Prometheus metrics tests ✅
│   ├── test_llm_metrics.py           # real LLM token/latency values in /metrics ✅
│   ├── test_network.py               # Phase 5 routing/DNS/SSL tests ✅
│   ├── test_agentic_engine.py        # Agent + orchestrator tests ✅
│   ├── test_agentic_api.py           # Agentic API tests ✅
│   └── test_llm.py                   # LLM client + backend tests ✅
├── docs/                             # Technical documentation
├── dev-scripts/ARCHITECTURE_REFERENCE.md  # Component/port reference tables
├── .github/workflows/ci.yml          # GitHub Actions CI (pytest, TESTING=1)
├── start_dap.py                      # DAP API server launcher (port 8001)
├── dap_dashboard.py                  # Live metrics dashboard (port 8081)
├── conftest.py                       # Pytest config (paths derived from __file__)
├── requirements.txt                  # Pinned dependencies (incl. aiosqlite)
├── .env.template                     # Env var docs (DAP_LLM_*, TESTING)
├── .venv/                            # Virtualenv, Python 3.14.6 (gitignored; canonical runner)
├── HANDOFF.md                        # Latest session handoff document
├── dap-grafana-dashboard.json        # Importable Grafana dashboard
├── dap_test.db                       # Test-suite SQLite DB (generated, gitignored)
├── server.log, dashboard.log         # Live service logs (gitignored)
├── .gitignore
└── .claude.json                      # Project context for agents (markdown despite the name)
```

> **Git repository**: `main`, remote `origin` = `https://github.com/mltmacster/devops-agentic-platform`.
> Published 2026-08-23; GitHub Actions CI (pytest on 3.12/3.13, `TESTING=1`) active and green.
> `core.autocrlf=false` is set to preserve per-file line endings.

---

## 🤖 AGENT INSTRUCTIONS — Compute Automation & System Maintenance

### ⚠️ CRITICAL: Post-Test Cleanup Protocol
After ANY test run, agent must execute the following cleanup sequence:

```bash
# One command does it all: kills headless instances (uvicorn servers, pytest,
# dashboard) and clears __pycache__ / *.pyc / .pytest_cache
bash .vault/scripts/run_computing.sh cleanup
```

> **Platform note:** `pgrep`/`free`/`wmic`/`ss` do not exist in Git Bash on Windows.
> `run_computing.sh` detects the platform internally (PowerShell `Get-CimInstance` +
> `taskkill //PID` on Windows; `pgrep`/`kill` elsewhere), so this one command is the
> entire protocol on every OS.

### 🔄 Daily/Weekly Maintenance Commands
Run these commands via `.vault/scripts/run_computing.sh`:

```bash
# Full cycle: Audit → Cleanup (recommended after long sessions)
bash .vault/scripts/run_computing.sh full

# Kill headless instances & clear cache only (quick cleanup)
bash .vault/scripts/run_computing.sh cleanup

# Run system audit only (no destructive actions)  
bash .vault/scripts/run_computing.sh audit
```

### 📋 System Health Checklist (Run Daily)
Run `bash .vault/scripts/run_computing.sh audit`, then confirm:
- [ ] No orphan Python/uvicorn processes reported
- [ ] Ports 8001/8081 in the expected state (intentionally running, or free)
- [ ] Disk usage < 80%
- [ ] Memory usage < 80%
- [ ] `.pytest_cache` / `__pycache__/` cleaned after test runs

### 🎯 When to Use Each Automation Mode
| Scenario | Command | What It Does |
|----------|---------|-------------|
| After test runs | `run_computing.sh cleanup` | Kills agents, clears cache |
| Long sessions (3+ hrs) | `run_computing.sh full` | Audit + cleanup |
| Before starting work | `run_computing.sh audit` | Check system health only |
| End of day | `run_computing.sh full` | Full housekeeping |

### 🚫 Agents MUST NOT
- Delete files in `.vault/` without explicit human approval
- Auto-purge old content from snapshots/archive
- Modify `VAULT_CONFIG.yaml` or `VAULT_COORDINATOR.yaml` 
- Run destructive commands without verification step
- Skip cleanup after test runs

---

## 📋 Phase Completion Status

### ✅ Phase 1: URL Formatting — COMPLETE
- `src/network/url_formatter.py` with `NetworkConfig`, `build_ide_url()`, `format_sandbox_response_urls()`
- URL formatting utilities integrated into sandbox API responses

### ✅ Phase 2: IDE Integration & Observability — COMPLETE
- **IDE WebSocket Server** (`src/api/ide/main.py`): Monaco Editor + LSP integration
  - `POST /api/ide/config` — Configure embedded editor (theme, language, extensions)
  - `GET /api/ide/config/current` — Current editor configuration
  - `GET /api/ide/lsp/capabilities` — LSP server capabilities
  - `GET /api/ide/lsp/info` — LSP server identity
  - `GET /api/ide/health/live` — Liveness probe (active sessions count)
  - `GET /api/ide/health/ready` — Readiness probe
  - `GET /api/ide/stats` — IDE service statistics
  - `WS /api/ide/ws/{session_id}` — WebSocket endpoint for Monaco Editor ↔ DAP communication
  
- **Prometheus Metrics** (`src/api/observability/main.py`):
  - `GET /api/observability/metrics` — Prometheus-compatible metrics text export
    - Gauge: `dap_ide_active_sessions`, `dap_workspace_total`, `dap_sandbox_running_number_of_sandboxes`
    - Counter: `dap_sandbox_total`, `dap_ai_tokens_total`, `dap_api_requests_total`
    - Histogram: `dap_ai_latency_seconds_bucket` (p95/p99)
  - `GET /api/observability/grafana/dashboard` — Grafana dashboard JSON (importable)
  - `GET /api/observability/grafana/datasource` — Prometheus datasource config for Grafana
  - `GET /api/observability/dashboard` — DAP-specific dashboard JSON with system health panels

- **Live Dashboard** (`dap_dashboard.py`):
  - Web UI at `http://localhost:8081/` with real-time metrics, health status, and system overview

### ✅ Phase 3: Agentic AI Engine — COMPLETE
- **Agents** (`src/agentic/`):
  - `CodeArchitectAgent` — classifies project type, selects stack, scaffolds 6 project types (REST API, Web App, Mobile, CLI, Microservice, Dashboard); `files_created` returns path strings
  - `DebuggerAgent` — 12 error types classified by phrase matching (no stop-word false positives); returns the matched spelling (`KeyError` from tracebacks, `Key Error` from human phrasing)
  - `TestGeneratorAgent` — generates unit + integration cases; `test_cases` = combined list, `tests_generated` = its length
  - `AgenticAIOrchestrator` — intent classification (debug → test → architect) + routing
- **API** (`src/api/agentic/main.py`):
  - `POST /api/agentic/run` — {sandbox_id, query} → {request_id, status, agent_type, result} (result tagged `engine: "llm" | "heuristic"`)
  - `GET /api/agentic/llm/status` — whether the LLM backend is configured
  - `GET /api/agentic/health/live` / `GET /api/agentic/health/ready`
- **LLM backend** (`src/agentic/llm.py`): opt-in via `DAP_LLM_API_KEY`; unconfigured → pure heuristic fallback (CI/keyless behavior unchanged). Each agent has a `SYSTEM_PROMPT` + `execute_async()` LLM path; sync `execute()` stays heuristic.

### ✅ Phase 4: Compute Automation — COMPLETE
- `.vault/scripts/run_computing.sh` with audit/cleanup/full modes
  - `audit` — Run system health checks (processes, disk, memory)
  - `cleanup` — Kill headless instances & clear caches
  - `full` — Full cycle: audit + cleanup
  
- AGENTS.md updated with compute automation rules and maintenance commands
- Windows-compatible: platform-branched process discovery (PowerShell `Get-CimInstance`), `taskkill //PID`, CRLF-safe parsing, `PY_CMD` interpreter resolution
- Verified 2026-08-23: `full` cycle killed 2/2 DAP processes (0 remaining), cleared caches, correct disk/memory/port report

### ✅ Phase 5: Networkability & Production Readiness — COMPLETE (2026-08-24: + compose production stack, Caddy/Let's Encrypt TLS, strict auth)
- **URL formatting utilities** (Phase 1) ✅
- **Sandbox network URLs in API responses** (Phase 1) ✅  
- **Public endpoint routing** (`src/network/public_routing.py`) ✅
  - `GET /api/network/` — API docs/index
  - `GET/POST /api/network/router/config` — Router configuration
  - `GET /api/network/router/status` — Router health status  
  - `POST /api/network/router/sandboxes/{id}` — Register a sandbox
  - `DELETE /api/network/router/sandboxes/{id}` — Deregister a sandbox
  - `GET /api/network/router/sandboxes` — List all sandboxes

- **DNS Configuration** (`src/network/dns_config.py`) ✅
  - `GET /api/network/dns/records` — Generate DNS records for a sandbox
  - `GET /api/network/dns/zone-file` — Export BIND zone file

- **SSL/TLS Certificates** (`src/network/ssl_manager.py`) ✅
  - `GET /api/network/ssl/certificates` — List certificates and their status (fixed crash bug)
  - `POST /api/network/ssl/generate/self-signed` — Generate self-signed cert for dev
  - `POST /api/network/ssl/generate/ca-signed` — Generate CA-signed cert

---

### 💡 Note: Networkability Design
- Public routing is in-memory (simple, no dependencies) — production would use NGINX/ALB
- Self-signed certs for local dev; Let's Encrypt integration documented for production
- DNS generation supports A/CNAME/SRV/MX records with BIND zone file export

---

## 📝 Current Session Notes (2026-08-23 — Health Audit & Docs Refresh)

- **Tests**: 118/118 passing (`TESTING=1 python -m pytest tests/ -q`)
- All audit fixes documented in `.vault/SOLUTIONS.md` — Solution 20
- Full session handoff in `HANDOFF.md` (project root)
- **Live processes left running intentionally** (user requested live preview):
  DAP server on 8001 (`server.log`), dashboard on 8081 (`dashboard.log`).
  Caches were still cleared per the cleanup protocol; only the two
  intentionally-started servers were preserved.

## 📝 Session Notes (2026-08-23 21:45 — Framework & Codebase Audit)

- Full audit: framework, modules, dependencies, databases, scripts, docs, live server
- **Found & fixed**: `src/database/__init__.py` dead import (`AsyncQueuePool` —
  doesn't exist in SQLAlchemy 2.0) 500'd every DB route on the live server's
  production branch. Removed (pool comes from `create_async_engine` defaults)
- **Archived** (vault, with RETIREMENT.md): `src/api/observability/metrics_collector.py`
  (SyntaxError, unused) + `src/agentic/plugin_registry.py` (NameError, unused)
- **Fixed**: requirements pins (uvicorn/pytest/pytest-asyncio now match the working
  0.52/9.x/1.x installs), missing `src/agentic/__init__.py` + `common/__init__.py`,
  `.gitignore` entry for `dap_test.db`
- **Vault**: SOLUTIONS.md Solution 21 · snapshot `2026-08-23-framework-audit/`
- **Known issue needing approval** (vault-protected): `.vault/VAULT_DEPLOYMENT.yaml`
  has a YAML syntax error (markdown checkboxes inside YAML) and a stale phase plan
- Live server restarted with `TESTING=1` (SQLite) so DB routes work in the live view
- Verified: 118/118 tests · 24/24 `src.*` modules import · 47 live API paths

## 📝 Session Notes (2026-08-23 — GitHub Publish + CI Fix)

- Repo initialized locally (`main`, `core.autocrlf=false`) and published at
  `https://github.com/mltmacster/devops-agentic-platform` (origin remote set)
- **CI fix** (SOLUTIONS.md Solution 22): `agent_orchestrator.get_agents()` annotated
  `Dict[AgentType]` (single-param) → TypeError at import on Python 3.12/3.13 (CI matrix);
  3.14 tolerates it, which masked the bug locally. Fixed to `Dict[AgentType, BaseAgent]`.
- Verified 118/118 on both 3.13 (fresh venv, matches CI) and 3.14
- `.gitignore` hardening: `dap_test.db` comment split to its own line; `docker/` →
  `/docker/` so `templates/docker/` deliverables are tracked

## 📝 Session Notes (2026-08-24 — Next-Phase Gap Closure)

- **Tests**: 187/187 passing (`TESTING=1 .venv/Scripts/python.exe -m pytest tests/ -q`;
  also verified twice on system python 3.14.6). Test count grew 118 → 187.
- **Five user-approved items completed** (SOLUTIONS.md Solutions 23–27):
  1. `GET /api/workspace/workspaces` list endpoint — root-cause fix: `Workspace.created_at`
     column was missing, so `list_all()` was dead code; ordering is now
     `created_at DESC, name DESC` (deterministic newest-first)
  2. Sandbox package renamed `src/sandbox-engine/` → `src/sandbox_engine/` (hyphen made it
     unimportable); `TRANSITIONS` state machine with 409/404 guards in the API;
     new `POST /sandboxes/{id}/start`
  3. Real LLM backend (`src/agentic/llm.py`) — opt-in via `DAP_LLM_API_KEY`, async path,
     heuristic fallback; `.env.template` added documenting `DAP_LLM_*` + `TESTING`
  4. `.venv` (Python 3.14.6, all pinned deps) — now the canonical test/serve runner;
     both live servers were switched to it
  5. Vault docs updated (SNAPSHOT_LOG, VAULT_OVERVIEW, this file, HANDOFF)
- **Also fixed**: psutil `NoSuchProcess` race in observability `/metrics`
  (Solution 26) — was an intermittently flaky determinism test
- **Live processes** (intentionally kept for user preview, venv python):
  DAP API on 8001, dashboard on 8081. Verify with `netstat -ano | grep LISTENING`.

## 📝 Session Notes (2026-08-24 — Production Build + User-Approved Vault Consistency Pass)

- **Tests: 218/219 passing** (`TESTING=1 .venv/Scripts/python.exe -m pytest tests/ -q`;
  the 1 skip is the Windows-only fake-podman test — it runs on CI Linux). Suite grew 187 → 219.
- **User-approved scope, all delivered** (SOLUTIONS.md Solutions 28–33 for the fixes discovered along the way):
  1. **Real sandbox execution backends** — `src/sandbox_engine/backends.py` (null /
     Podman / gVisor via `DAP_SANDBOX_RUNTIME=auto|podman|runsc|null`, `--network none`,
     failed op → ERROR parking); surfaced in `/health` + `/api/sandbox/status`
     (SOLUTIONS 31: no-container branch must park ERROR)
  2. **Production deployment** — `templates/docker/Dockerfile` + `DOCKERCOMPOSE_PROD.yml`
     (postgres + api + dashboard + Caddy/Let's Encrypt) + `Caddyfile`; `init_db()` in
     app lifespan; `docs/DEPLOYMENT_GUIDE.md` §0 quick start (SOLUTION 33: auth lookup
     degrades to unknown-user when the identity store isn't initialized)
  3. **Real auth persistence** — `users` table, PBKDF2 (600k), HS256 JWT pairs,
     `DAP_AUTH_STRICT=1` fail-closed; dev default stays fail-open (SOLUTION 30: the
     dev-fallback JWT key was a str → TypeError on every real token)
  4. **Real LLM metrics** — `dap_ai_tokens_total` / `dap_ai_requests_total` /
     `dap_ai_latency_seconds_*` fed from the `LLMStats` registry; 5 new tests
  5. **Vault consistency pass** — `VAULT_DEPLOYMENT.yaml` v1 retired to
     `archive/2026-08-24_vault-deployment-v1/` (+RETIREMENT.md) and replaced by valid
     v2.0.0; versioned fixes to `VAULT_COORDINATOR.yaml` v1.1, `VAULT_CONFIG.yaml` v1.1,
     `ARCHITECTURE.md` v1.1, `.gitkeep-README.md` v1.1, `validate_vault.sh` v1.1
     (path/interpreter/REQUIRED_FILES); `.gitkeep-README.md` count fixed 15 → 33.
     `bash .vault/scripts/validate_vault.sh` → passed.
- **Learnings**: never use async autouse fixtures in this repo (SOLUTION 32);
  vault YAML must stay checkbox-free and be `yaml.safe_load`-validated (SOLUTION 28);
  all vault file replacements show their version header + prior-version location.
- **Live processes**: both preview servers (8001/8081) running on venv python;
  restart after this commit picks up the new endpoints (`/auth/register`, sandbox
  `runtime`, real AI metrics). Caches cleared manually (`.pytest_cache`, `__pycache__`)
  — `run_computing.sh cleanup` was NOT used (it would kill the previews).
- **Published**: commit + push to `origin/main`; CI (3.12/3.13) re-verified green.
- **Next** (see `HANDOFF.md`): first real production deploy (host + domain),
  live podman sandbox verification, optional RBAC integration tests.
