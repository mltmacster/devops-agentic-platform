# Handoff — DAP (DevOps Agentic Platform)

Project root: `C:\Users\mltma\Downloads\test\devops-agentic-platform`
Last session: **2026-08-23 — full framework / codebase / health / functionality audit** (replaces prior handoff)

## Goal of next session

All five roadmap phases remain COMPLETE. Obvious gaps to close next:

1. **Add a GitHub remote** — the repo is now initialized (local `main` branch, openable in GitHub Desktop); create a remote on github.com and `git push -u origin main` to activate the CI workflow.
2. **Create a virtualenv** — everything runs on system Python 3.14.6; `requirements.txt` pins are now aligned with the working env, so `pip install -r` + venv should be faithful.
3. **Real LLM backend for the agentic engine** — all three agents are heuristic/keyword-based (fine for tests, no model calls).
4. **Real sandbox engine** — `src/sandbox-engine/vm_manager.py` is an in-memory stub. Note: the hyphenated directory name makes it **unimportable** as a Python package; rename to `src/sandbox_engine/` before wiring it in.
5. **Optional (needs approval)** — fix `.vault/VAULT_DEPLOYMENT.yaml`: YAML syntax error (markdown `- [ ]` checkboxes inside list items) + stale phase plan. Vault-protected, so human approval required.

## State of play (verified this session)

- **Tests: 118/118 passing** with `TESTING=1` (SQLite backend). Do NOT run the suite without `TESTING=1` — it targets asyncpg→localhost:5432 (no PostgreSQL here) and fails with ConnectionRefused.
- **Imports: 24/24** live `src.*` modules import cleanly; `compileall` clean across src/tests/root scripts.
- **Fixed this session** (SOLUTIONS.md **Solution 21**):
  - `src/database/__init__.py` dead import `AsyncQueuePool` (nonexistent in SQLAlchemy 2.0; killed every DB route on the live server's production branch) — removed, branches merged.
  - Archived two dead modules to `.vault/archive/2026-08-23_dead-modules/` (with RETIREMENT.md): `metrics_collector.py` (SyntaxError) + `plugin_registry.py` (NameError).
  - requirements pins widened (uvicorn/pytest/pytest-asyncio), `src/agentic/__init__.py` + `common/__init__.py` added, `dap_test.db` gitignored.
- **Live processes:** DAP API on **8001** (`python start_dap.py --port 8001`, **started with `TESTING=1`** so DB routes work against `dap_test.db`; log `server.log`), dashboard on **8081** (`python dap_dashboard.py`, log `dashboard.log`). Dashboard polls 8001. Verify with `netstat -ano | grep LISTENING`.
- **Live verification:** 47 API paths exposed; all health endpoints 200; workspace + sandbox creation now 201/200 (were 500 pre-fix); metrics + Grafana + network + SSL + IDE endpoints 200.
- Vault: snapshot `.vault/snapshots/2026-08-23-framework-audit/`, SNAPSHOT_LOG entry, VAULT_OVERVIEW matrix current.

## Environment gotchas (Windows / Git Bash)

- `python` = Python 3.14.6 (C:\Python314); `python3` = **Microsoft Store stub** that fails. Use `python`.
- Git Bash: `pgrep`/`wmic`/`free`/`ss`/`rev` do NOT exist. `taskkill /PID` must be written `taskkill //PID`. PowerShell output is CRLF — strip `\r`.
- `df -h /` label contains spaces — never parse by column index from the left.
- No venv; git repo initialized 2026-08-23 (local only, no remote); no root `docker-compose.yml` (real template: `templates/docker/DOCKERCOMPOSE_FULL.yml`).
- `.claude.json` is actually **markdown** despite the name — don't JSON-parse it.
- Project files use CRLF line endings; keep it that way.

## Documentation map (authoritative)

- `AGENTS.md` — vault rules, compute-automation protocol, current root/vault trees, phase status, session notes
- `.vault/VAULT_OVERVIEW.md` — architecture diagram, service status matrix, phase sections, open TODOs
- `.vault/SOLUTIONS.md` — 21 documented solutions (latest: this audit)
- `docs/ARTIFACT_STATUS_DASHBOARD.md` — v0.1.0 planning dashboard (banner marks it partially stale; header stamped per session)
- `docs/SSESSION_HANDOFF_PROTOCOL.md` — session handoff protocol (fill the dashboard each session)
