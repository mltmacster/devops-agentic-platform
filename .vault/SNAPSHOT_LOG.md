# ════════════════════════════════════════════════
# VAULT SNAPSHOT LOG — All snapshots tracked here
# ════════════════════════════════════════════════

## Snapshot Entry Format
```
[YYYY-MM-DD HH:MM] SERVICE | TYPE | Description | Files Changed | Author
```

---

## Snapshots

### [2026-08-21 07:35] WORKSPACE | SNAPSHOT | Initial workspace CRUD implementation
- **Description**: Implemented full workspace lifecycle management with async SQLAlchemy + SQLite backend
- **Files Changed**: 
  - `src/api/workspace/main.py` (245 lines)
  - `src/database/__init__.py` (105 lines)
  - `src/database/models.py` (123 lines)  
  - `src/database/workspace_repo.py` (75 lines)
- **Author**: Claude Bionic
- **Tests**: 11 passing (test_create_*, test_get_*, test_update_*, test_delete_*)

### [2026-08-21 07:45] SANDBOX | SNAPSHOT | Full sandbox lifecycle management
- **Description**: Implemented sandbox CRUD with state transitions (create/stop/suspend/resume/delete)
- **Files Changed**:
  - `src/api/sandbox/main.py` (248 lines)
  - `src/database/sandbox_repo.py` (75 lines)
- **Author**: Claude Bionic
- **Tests**: 11 passing (test_create_*, test_status_*, test_state_transitions)

### [2026-08-21 07:55] AUTH | SNAPSHOT | Auth service with RBAC engine
- **Description**: Implemented auth endpoints (login/refresh/me) + full RBAC permission system
- **Files Changed**:
  - `src/api/auth/main.py` (246 lines) — 8 endpoints implemented
  - `src/api/auth/rbac.py` (153 lines) — Role-based + scope-based permission engine
  - `src/api/auth/session_manager.py` (124 lines) — JWT validation + MFA coordination
- **Author**: Claude Bionic
- **Tests**: 13 passing (test_login_*, test_rbac_*, test_health_)

### [2026-08-21 07:05] MAIN | SNAPSHOT | Unified FastAPI entry point
- **Description**: Created `src/main.py` that includes all microservices under /api/ prefix
- **Files Changed**: `src/main.py` (74 lines)

### [2026-08-23 20:50] HEALTH-AUDIT | SNAPSHOT | Health audit — agentic engine fixes + Windows compute automation
- **Description**: Codebase health audit & debug/fix — fixed 12 failing agentic tests (agent contract mismatches), made `run_computing.sh` Windows-compatible, archived shadowed `src/network.py` duplicate, added CI workflow. Details: SOLUTIONS.md Solution 20.
- **Files Changed**:
  - `src/agentic/code_architect.py`, `debugger.py`, `test_generator.py`, `agent_orchestrator.py` (contract fixes)
  - `src/api/agentic/main.py` (AgentType name-lookup)
  - `.vault/scripts/run_computing.sh` (Windows platform branch)
  - `conftest.py` + 8 test files (CWD-independent paths)
  - `requirements.txt` (added aiosqlite, widened FastAPI pin)
  - `dap_dashboard.py` (raw-string HTML fix)
  - `.github/workflows/ci.yml` (new)
  - `src/network.py` (removed — archived to `archive/2026-08-23_network-py-duplicate/`)
- **Author**: Claude Bionic
- **Tests**: 118/118 passing (`TESTING=1 python -m pytest tests/ -q`)
- **Snapshot Dir**: `.vault/snapshots/2026-08-23-health-audit/`

### [2026-08-24 00:23] WORKSPACE+SANDBOX+AGENTIC | SNAPSHOT | Next-phase gap closure — workspace list, sandbox engine + state machine, LLM backend, venv
- **Description**: Completed 5 user-approved items: (1) `GET /api/workspace/workspaces` list endpoint (root-cause fix: `Workspace.created_at` column + deterministic `list_all()` ordering); (2) sandbox package renamed `sandbox-engine` → `sandbox_engine` (was unimportable), `TRANSITIONS` state machine with 409/404 guards, new `POST /sandboxes/{id}/start`; (3) opt-in real LLM backend (`src/agentic/llm.py`, `DAP_LLM_API_KEY`) with heuristic fallback + `GET /api/agentic/llm/status`; (4) `.venv` (Python 3.14.6, all pinned deps) as canonical runner; (5) vault doc updates. Also fixed psutil race in observability `/metrics` (Solution 26). Details: SOLUTIONS.md Solutions 23–27.
- **Files Changed**:
  - `src/api/workspace/main.py` (list endpoint), `src/database/models.py` (`created_at`), `src/database/workspace_repo.py`
  - `src/sandbox_engine/vm_manager.py` + `__init__.py` (renamed from `src/sandbox-engine/`), `src/api/sandbox/main.py`
  - `src/agentic/llm.py` (new), `code_architect.py`, `debugger.py`, `test_generator.py`, `plugin_interface.py`, `agent_orchestrator.py`, `__init__.py`
  - `src/api/agentic/main.py` (`/run` async, `/llm/status`), `src/api/observability/main.py` (psutil race fix)
  - `tests/test_workspace_api.py` (+4), `tests/test_sandbox_api.py` (+4), `tests/test_llm.py` (new, 22), `tests/test_sandbox_engine.py` (new, 27)
  - `.env.template` (new), `.gitignore`, `conftest.py`, `requirements.txt` (pre-change copies in snapshot dir)
- **Author**: Claude Bionic
- **Tests**: 187/187 passing (system python 3.14.6 ×2, venv ×1)
- **Snapshot Dir**: `.vault/snapshots/2026-08-24-next-phase/`

### [2026-08-24 14:30] PRODUCTION | SNAPSHOT | Production build — sandbox backends, real auth, LLM metrics, deploy stack + user-approved vault consistency pass
- **Description**: Completed the three open next-steps from the prior handoff: (1) real sandbox execution backends (null/Podman/gVisor, `DAP_SANDBOX_RUNTIME`, `--network none`, ERROR parking on failure); (2) production deployment artifacts (Dockerfile, DOCKERCOMPOSE_PROD.yml, Caddyfile) + real auth persistence (`users` table, PBKDF2, HS256 JWT, `DAP_AUTH_STRICT`) + `init_db()` in app lifespan; (3) real LLM token/latency counters into `/metrics` + `/metrics/summary`. Then the user-approved vault consistency pass: retired `VAULT_DEPLOYMENT.yaml` v1 (invalid YAML + stale roadmap) into `archive/2026-08-24_vault-deployment-v1/` with RETIREMENT.md, wrote v2.0.0, versioned fixes to VAULT_COORDINATOR/CONFIG, ARCHITECTURE, .gitkeep-README, validate_vault.sh; SOLUTIONS.md Solutions 28–33.
- **Files Changed**:
  - NEW: `src/sandbox_engine/backends.py`, `src/api/auth/credentials.py`, `src/database/user_repo.py`, `templates/docker/Dockerfile`, `templates/docker/DOCKERCOMPOSE_PROD.yml`, `templates/docker/Caddyfile`, `tests/test_auth_users.py` (15), `tests/test_sandbox_backends.py` (12), `tests/test_llm_metrics.py` (5)
  - `src/sandbox_engine/vm_manager.py` (+`__init__.py`) — backend wiring, runtime/container_id, ERROR parking
  - `src/api/auth/main.py` — register/real login/refresh-rotation/`/me`, strict & dev modes
  - `src/api/sandbox/main.py` (runtime in status), `src/main.py` (lifespan init_db, runtime in /health), `src/agentic/llm.py` (LLMStats), `src/api/observability/main.py` (real AI values), `src/database/models.py` (User), `dap_dashboard.py` (`DAP_API_URL` env), `templates/docker/Dockerfile.template` (stale path fix)
  - Vault: `VAULT_DEPLOYMENT.yaml` v1→archive + v2, `VAULT_COORDINATOR.yaml` v1.1, `VAULT_CONFIG.yaml` v1.1, `ARCHITECTURE.md` v1.1, `.gitkeep-README.md` v1.1, `scripts/validate_vault.sh` v1.1, `SOLUTIONS.md` (28–33), `VAULT_OVERVIEW.md`
  - Docs: `AGENTS.md`, `HANDOFF.md`, `.env.template`, `docs/DEPLOYMENT_GUIDE.md`
- **Author**: Claude Bionic
- **Tests**: 218/219 passing (1 skip = Windows-only fake-podman test; runs on CI Linux) — `TESTING=1 .venv/Scripts/python.exe -m pytest tests/ -q`
- **Vault validation**: `bash .vault/scripts/validate_vault.sh` → passed (all YAML valid)
- **Snapshot Dir**: `.vault/snapshots/2026-08-24-production/` (33 pre-change files)

### [2026-08-23 21:45] FRAMEWORK-AUDIT | SNAPSHOT | Full framework & codebase audit — dead import fix, dead module archival
- **Description**: Complete audit of framework, modules, dependencies, databases, scripts, docs, and live server. Fixed the `AsyncQueuePool` dead import in the database layer (500s on all DB routes in production mode), archived 2 dead modules, aligned requirements pins, added missing `__init__.py` files, gitignored `dap_test.db`. Details: SOLUTIONS.md Solution 21.
- **Files Changed**:
  - `src/database/__init__.py` (dead import removed, branches merged)
  - `src/api/observability/metrics_collector.py` (archived → `archive/2026-08-23_dead-modules/`)
  - `src/agentic/plugin_registry.py` (archived → `archive/2026-08-23_dead-modules/`)
  - `src/agentic/__init__.py`, `src/agentic/common/__init__.py` (new, docstring-only)
  - `requirements.txt` (pin widening), `.gitignore` (dap_test.db)
  - Docs: AGENTS.md, VAULT_OVERVIEW.md, ARTIFACT_STATUS_DASHBOARD.md, HANDOFF.md
- **Author**: Claude Bionic
- **Tests**: 118/118 passing (`TESTING=1`)
- **Snapshot Dir**: `.vault/snapshots/2026-08-23-framework-audit/`

### [2026-08-24 17:19] CI-FIX | SNAPSHOT | CI red → green: force in-memory sandbox backend in tests, shebang-at-byte-0 fake podman, state-tolerant pause/resume
- **Description**: Diagnosed the failed CI run (32764412039, commit `3290e77`): GitHub `ubuntu-latest` runners preinstall Podman 5.8.4, so `select_backend()` auto-detected real podman and every manager-using test pulled `ubuntu:24.04` (suite 5s→45s, `test_full_lifecycle_flow` failed). Fixed with `tests/conftest.py` (`DAP_SANDBOX_RUNTIME=null` for the whole suite); repaired the fake-podman fixture (leading newline broke the shebang → ENOEXEC; now LF + byte-0 shebang, state-tracking); added `state()` to the backend protocol and state-tolerant `_start_backend`/`_stop_backend` in `vm_manager.py` (real podman cannot pause an exited container). SOLUTIONS.md Solutions 34–36.
- **Files Changed**:
  - `tests/conftest.py` (new — env-agnostic suite)
  - `src/sandbox_engine/backends.py` (`state()` on protocol + null + podman backends)
  - `src/sandbox_engine/vm_manager.py` (state-aware start/stop/suspend/resume)
  - `tests/test_sandbox_backends.py` (fake-podman fixture + lifecycle assertions)
  - `.gitignore` (`.venv-wsl/` ignored)
  - Vault: `SOLUTIONS.md` (34–36), `ARCHITECTURE.md` v1.2, `VAULT_OVERVIEW.md` (test note), `SNAPSHOT_LOG.md`, `AGENTS.md` (session notes + rule)
- **Author**: Claude Bionic (handoff continuation)
- **Tests**: 218 passed / 1 skipped on Windows (5.6s); **219/219 in the WSL Ubuntu 26.04 CI replica** (real podman 5.7 installed) in 4.3s — the exact CI analog, in both LF and CRLF trees
- **Snapshot Dir**: n/a — no pre-change snapshot this session (fixes were uncommitted working-tree edits on top of `3290e77`)

---


### [2026-08-25 02:30] SANDBOX+DEPLOY | SNAPSHOT | Live podman verify (30/30) + production deploy prep
- **Description**: (1) Re-ran `dev-scripts/live_verify_sandbox.sh` on the WSL
  Ubuntu 26.04 runtime host after the network-check fix — **30/30 ALL GREEN**
  against real podman 5.7.0 (SOLUTION 37 acceptance). (2) First-ever run of the
  production compose stack (Docker Desktop 29.7.2, `DAP_PUBLIC_HOST=localhost`):
  found and fixed 5 blockers (SOLUTION 38: build context, healthcheck path,
  dashboard JS sentinel + browser URL, port exposure, Caddyfile `/health`) and a
  security gap (SOLUTION 39: strict-mode route guard + registration closure);
  verified build, TLS, strict auth, dashboard, Postgres persistence, and the
  `init_db` migration path, then tore down.
- **Files Changed**:
  - `templates/docker/DOCKERCOMPOSE_PROD.yml` (context `../..`, ports unpublished, podman-socket option block)
  - `templates/docker/Dockerfile` (healthcheck `/health`)
  - `templates/docker/Caddyfile` (`/health*` → api)
  - `dap_dashboard.py` (`__DAP_BROWSER_API__` sentinel + `DAP_BROWSER_API_URL`)
  - `docs/DEPLOYMENT_GUIDE.md` (`.env` placement, Caddy-only exposure, "Real sandbox execution in production")
  - `src/api/auth/route_guard.py` (new — StrictAuthMiddleware)
  - `src/api/auth/main.py` (registration closed in strict mode)
  - `src/main.py` (middleware registration)
  - `tests/test_route_guard.py` (new — 8 tests)
  - Vault: `SOLUTIONS.md` (37–39), `VAULT_OVERVIEW.md`, `SNAPSHOT_LOG.md`, `AGENTS.md`, `HANDOFF.md`, `metrics/`
- **Author**: Claude Bionic (handoff continuation)
- **Tests**: 237 passed / 1 skipped on Windows venv 3.14.6 (was 229); live verify 30/30 (WSL, real podman)
- **Snapshot Dir**: `.vault/snapshots/2026-08-25-deploy-prep/` (pre-change copies of all touched files)

## Snapshot Verification
| ID | Status | Last Verified | Notes |
|----|--------|---------------|-------|
| 2026-08-21 07:35 | ✅ Validated | 2026-08-21 | All 11 tests pass |
| 2026-08-21 07:45 | ✅ Validated | 2026-08-21 | All 11 tests pass |
| 2026-08-21 07:55 | ✅ Validated | 2026-08-21 | All 13 tests pass |
| 2026-08-23 20:50 | ✅ Validated | 2026-08-23 | All 118 tests pass |
| 2026-08-23 21:45 | ✅ Validated | 2026-08-23 | All 118 tests pass |
| 2026-08-24 00:23 | ✅ Validated | 2026-08-24 | All 187 tests pass |
| 2026-08-24 14:30 | ✅ Validated | 2026-08-24 | 218/219 (1 Windows-only skip) · vault validation passed |
| 2026-08-24 17:19 | ✅ Validated | 2026-08-24 | 219/219 in WSL CI replica (real podman present) · suite env-agnostic via tests/conftest.py |
| 2026-08-25 02:30 | ✅ Validated | 2026-08-25 | 237/238 (1 Windows-only skip) · live verify 30/30 · compose dry run green · vault validation passed |
