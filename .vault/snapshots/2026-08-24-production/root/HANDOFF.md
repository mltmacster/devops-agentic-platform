# Handoff — DAP (DevOps Agentic Platform)

Project root: `C:\Users\mltma\Downloads\test\devops-agentic-platform`
Last session: **2026-08-24 — next-phase gap closure** (replaces prior handoff)

## State of play (verified this session)

All five roadmap phases remain COMPLETE. The 5 user-approved gap items are done (SOLUTIONS.md Solutions 23–27):

1. ✅ **Workspace list endpoint** `GET /api/workspace/workspaces` — root-cause fix was the missing `Workspace.created_at` column (made `list_all()` dead code); ordering now `created_at DESC, name DESC`.
2. ✅ **Sandbox engine** — package renamed `src/sandbox-engine/` → `src/sandbox_engine/` (hyphen made it unimportable); `TRANSITIONS` state machine (CREATING provisional, DELETED terminal, 409/404 guards in the API); new `POST /sandboxes/{id}/start`.
3. ✅ **Real LLM backend** — `src/agentic/llm.py`, opt-in via `DAP_LLM_API_KEY` (async path; sync `execute()` stays heuristic so CI/keyless behavior is unchanged); `GET /api/agentic/llm/status` (live = heuristic without a key); `.env.template` added.
4. ✅ **Virtualenv** — `.venv` (Python 3.14.6, all pinned deps) is now the canonical runner; both live servers run on it.
5. ✅ **Vault docs + commit/push** — SOLUTIONS.md 23–27, SNAPSHOT_LOG entry, VAULT_OVERVIEW matrix, AGENTS.md session notes, this handoff.

- **Tests: 187/187 passing** (`TESTING=1 .venv/Scripts/python.exe -m pytest tests/ -q`; also 187/187 on system 3.14.6). Per file: workspace 15, sandbox_api 15, sandbox_engine 39, llm 22, agentic_engine 4, agentic_api 20, auth 13, ide 11, network 20, observability 28.
- **Do NOT run the suite without `TESTING=1`** — it targets asyncpg→localhost:5432 (no PostgreSQL here) and fails with ConnectionRefused.
- **Published**: `https://github.com/mltmacster/devops-agentic-platform` (`origin/main`). CI = GitHub Actions pytest on 3.12/3.13 with `TESTING=1`; green after the annotation fix (Solution 22).
- **Live processes (intentionally kept for user preview, venv python):** DAP API on **8001** (`python start_dap.py --port 8001` with `TESTING=1`, log `server.log`), dashboard on **8081** (`python dap_dashboard.py`, log `dashboard.log`). Verify with `netstat -ano | grep LISTENING`.
- Vault: snapshot `.vault/snapshots/2026-08-24-next-phase/` + SNAPSHOT_LOG entry + VAULT_OVERVIEW matrix.

## Goal of next session

1. **Real sandbox execution** — `src/sandbox_engine/vm_manager.py` is an in-memory state-machine stub. Wire real container execution (Podman, or gVisor/`runsc` if available; otherwise a documented no-op backend) behind the same `VMManager` interface. The API + state machine + 39 tests already enforce lifecycle safety, so only the execution backend changes.
2. **Remote / production deployment** — take the platform beyond localhost: hosted or reverse-proxied API + dashboard, real auth persistence (still stubbed), real RBAC storage. Phase 5 network code (public routing / DNS / SSL) is in-memory + self-signed — production would use NGINX/ALB + Let's Encrypt.
3. **Fix `.vault/VAULT_DEPLOYMENT.yaml` (needs user approval)** — vault-protected; has a YAML syntax error (markdown `- [ ]` checkboxes inside YAML list items) + a stale phase plan. Do NOT fix unilaterally; ask the user first.
4. **Optional** — wire LLM token/latency counters from `src/agentic/llm.py` into observability `/metrics` (currently synthesized static sample values).

## Environment gotchas (Windows / Git Bash)

- `python` = Python 3.14.6 (C:\Python314); `python3` = **Microsoft Store stub** that fails. Prefer the **venv**: `.venv/Scripts/python.exe` (canonical). `py -3.13` exists if a 3.13 repro is ever needed (CI covers 3.12/3.13).
- Git Bash: `pgrep`/`wmic`/`free`/`ss`/`rev` do NOT exist. `taskkill /PID` must be written `taskkill //PID`. PowerShell output is CRLF — strip `\r`. Heredocs truncate on very long content — use `edit_file_tool` or a Python write for big files.
- `df -h /` label contains spaces — never parse by column index from the left.
- `edit_file_tool` JSON-escaping quirk: strings containing double quotes inside single-quoted Python literals can fail to match; workaround = byte-level Python replace via shell.
- `run_computing.sh cleanup` kills the two intentionally-live preview servers — when the user's preview must stay up, clean caches manually instead (`.pytest_cache`, `__pycache__`).
- No root `docker-compose.yml` (real template: `templates/docker/DOCKERCOMPOSE_FULL.yml`).
- `.claude.json` is actually **markdown** despite the name — don't JSON-parse it.
- Project files use CRLF line endings; keep it that way (git `core.autocrlf=false`). Full-file rewrites via `replace_file` emit LF — harmless, or convert back to CRLF.

## Documentation map (authoritative)

- `AGENTS.md` — vault rules, compute-automation protocol, current root tree, phase status, session notes
- `.vault/VAULT_OVERVIEW.md` — architecture diagram, service status matrix, phase sections, open TODOs
- `.vault/SOLUTIONS.md` — 27 documented solutions (latest: Solutions 23–27, this session)
- `.vault/SNAPSHOT_LOG.md` — snapshot history (latest: `2026-08-24-next-phase`)
- `docs/ARTIFACT_STATUS_DASHBOARD.md` — v0.1.0 planning dashboard (banner marks it partially stale; header stamped per session)
- `docs/SSESSION_HANDOFF_PROTOCOL.md` — session handoff protocol (fill the dashboard each session)
- `.env.template` — env var reference (`DAP_LLM_*`, `TESTING`)
