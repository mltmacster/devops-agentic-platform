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

---

## Snapshot Verification
| ID | Status | Last Verified | Notes |
|----|--------|---------------|-------|
| 2026-08-21 07:35 | ✅ Validated | 2026-08-21 | All 11 tests pass |
| 2026-08-21 07:45 | ✅ Validated | 2026-08-21 | All 11 tests pass |
| 2026-08-21 07:55 | ✅ Validated | 2026-08-21 | All 13 tests pass |
| 2026-08-23 20:50 | ✅ Validated | 2026-08-23 | All 118 tests pass |
| 2026-08-23 21:45 | ✅ Validated | 2026-08-23 | All 118 tests pass |
