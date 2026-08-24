# Handoff — DAP (DevOps Agentic Platform)

Project root: `C:\Users\mltma\Downloads\test\devops-agentic-platform`

## Goal of next session

All five roadmap phases (URL formatting → IDE WS + Prometheus → Agentic AI → Compute automation → Networkability) are **COMPLETE** and verified. No user argument was passed; inferred next work is production-readiness beyond the roadmap:

1. **Initialize a git repository** — the project has **no `.git`**. The `.github/workflows/ci.yml` that was created has nowhere to run until a repo exists.
2. **Create a virtualenv** — everything currently runs on system Python 3.14.6; the compute audit flags two real installs (3.14 + 3.13) plus a Microsoft Store `python3` stub. A `.venv` with `requirements.txt` makes the platform reproducible.
3. **Real LLM backend for the agentic engine** — `src/agentic/plugin_interface.py` defines the agent contract; all three agents are currently heuristic/keyword-based (fine for tests, no actual AI calls).
4. **Real sandbox engine** — `src/sandbox-engine/` is in-memory; no actual VM/container lifecycle.

If the user redirects, follow them; these are the obvious gaps.

## State of play

- **Test suite: 118/118 passing** with `TESTING=1` (SQLite backend; no PostgreSQL needed). Do NOT run the suite without `TESTING=1` — it tries asyncpg→localhost:5432 and 22 tests fail with ConnectionRefused (environment issue, not a bug).
- **Live processes (still running as of handoff):** DAP API server on **8001** (`python start_dap.py --port 8001`, log `server.log`), live dashboard on **8081** (`python dap_dashboard.py`, log `dashboard.log`). The dashboard polls the 8001 API. Verify with `netstat -ano | grep LISTENING`; restart both if dead.
- Full health audit completed this session: 12 agentic test failures fixed, compute-automation script fixed for Windows, dead duplicate `src/network.py` archived, CI workflow added, AGENTS.md Phase 3 marked COMPLETE. All fixes documented in `.vault/SOLUTIONS.md` **Solution 20** (read it — it has the full root-cause list and verification commands).
- Compute automation works end-to-end on this machine: `.vault/scripts/run_computing.sh {audit|cleanup|full}`.

## Environment gotchas (Windows / Git Bash)

- `python` = Python 3.14.6 (C:\Python314); `python3` resolves to a **Microsoft Store stub** that fails. Use `python` everywhere.
- Shell is Git Bash. `pgrep`, `wmic`, `free`, `ss`, `rev` do NOT exist. `taskkill /PID` must be written `taskkill //PID` (MSYS path mangling). PowerShell output is CRLF — strip `\r` before use.
- `df -h /` label contains spaces ("C:/Program Files/Git") — never parse by column index from the left.
- FastAPI installed is **0.141.1** (requirements pin was widened to `<1.0` to match reality).
- There is no venv and no git repo (see above).

## Open decisions (next agent must decide)

- **Git init**: plain repo? default branch name? remote (GitHub)? The user has never explicitly asked for a remote — ask before pushing.
- **venv vs system Python**: creating `.venv` changes how `start_dap.py`/tests are launched (AGENTS.md quick commands assume `python`). Decide and update AGENTS.md accordingly.
- **LLM integration**: which provider/API for the agentic engine, and whether a mock mode stays the default for tests (tests must remain hermetic — no network calls in pytest).
- **Dashboard port convention**: dashboard hardcodes `DAP_API = http://localhost:8001` (dap_dashboard.py); `start_dap.py` defaults to 8000. Pick one canonical port and align both + AGENTS.md.
- AGENTS.md cleanup protocol says kill instances after *any* test run, but the user wants the server kept alive for preview — working compromise (established last session): clear caches after test runs, keep intentionally-started servers running.

## Standing user preferences

- "keep it clean, no extra comments" — minimal code comments only where non-obvious.
- "keeping both processes should offer resilience in the platform" — IDE WebSocket AND Prometheus both stay.
- `.vault/` is protected: never delete vault content; document fixes in `.vault/SOLUTIONS.md`; archive retired code with a RETIREMENT.md (see `.vault/archive/2026-08-23_network-py-duplicate/` as the template).
- The user dislikes agents stopping mid-task — push through to a verified end state.

## Skills to use

- `handoff` (if the next session itself hands off again)
- `agent-workflow-designer` / `mcp-builder` — if building the real LLM backend for the agentic engine
- `docker-development` / `ci-cd-pipeline-builder` — if wiring real sandbox execution or strengthening CI
- `kubernetes-operator` / `chaos-engineering` — only if the user asks for production deployment work

## Artifacts (reference, do not duplicate)

| What | Where |
|---|---|
| Roadmap + phase status + agent rules + compute-automation protocol | `AGENTS.md` |
| All fixes from the health audit (root causes + verification) | `.vault/SOLUTIONS.md` → Solution 20 |
| CI workflow | `.github/workflows/ci.yml` |
| Compute automation (Windows-fixed) | `.vault/scripts/run_computing.sh` |
| Agentic agents (fixed) | `src/agentic/` (debugger, code_architect, test_generator, agent_orchestrator) |
| Agentic API | `src/api/agentic/main.py` |
| FastAPI root app | `src/main.py` |
| Dashboard | `dap_dashboard.py` (port 8081) |
| Launcher | `start_dap.py` (default port 8000; run with `--port 8001`) |
| Network module (Phase 5) | `src/network/` (url_formatter, public_routing, dns_config, ssl_manager) |
| Test suite (118 tests) | `tests/` (run: `TESTING=1 python -m pytest tests/ -q`) |
| Retired duplicate | `.vault/archive/2026-08-23_network-py-duplicate/` |
| Vault config/rules | `.vault/VAULT_CONFIG.yaml`, `VAULT_COORDINATOR.yaml`, `LIFECYCLE_PROTOCOL.md` (read-only) |

## Commands

```bash
cd C:/Users/mltma/Downloads/test/devops-agentic-platform
TESTING=1 python -m pytest tests/ -q          # full suite (118)
python start_dap.py --port 8001               # API server (bg: nohup ... > server.log 2>&1 &)
python dap_dashboard.py --port 8081           # live dashboard (bg same pattern)
bash .vault/scripts/run_computing.sh audit    # health only
bash .vault/scripts/run_computing.sh cleanup  # kill DAP processes + clear caches
```
