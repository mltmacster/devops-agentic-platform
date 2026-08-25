# Handoff — DAP (DevOps Agentic Platform)

Project root: `C:\Users\mltma\Downloads\test\devops-agentic-platform`
Last session: **2026-08-24 — CI red→green fix (Solutions 34–36)** (replaces prior handoff;
previous session: production build + user-approved vault consistency pass, `3290e77`)

## State of play (verified this session)

The CI failure on `3290e77` (run 32764412039, both 3.12/3.13 jobs) is fixed and
published green. Three bugs (SOLUTIONS.md 34–36):
1. **CI drove real podman** — GitHub `ubuntu-latest` runners preinstall Podman
   5.8.4; `select_backend()` auto-detected it and every manager test pulled
   `ubuntu:24.04`. New `tests/conftest.py` forces `DAP_SANDBOX_RUNTIME=null` for
   the whole suite (AGENTS.md rule 7: the suite must stay environment-agnostic).
2. **Fake-podman shebang not at byte 0** — leading `\n` from the triple-quoted
   string → ENOEXEC from Python (`OSError: Exec format error`; manual dash runs
   masked it via source-fallback). Fixture now LF + `lstrip("\n")`, state-tracking,
   exact podman call-count assertions.
3. **Latent prod bug: real podman cannot pause an exited container** (exit 125).
   `state()` added to the backend protocol; `_start_backend()`/`_stop_backend()`
   in `vm_manager.py` are now state-tolerant (stop→suspend is a no-op, resume
   re-starts an exited container).

Verified: 218 passed / 1 skipped on Windows (5.6s); **219/219 in the WSL Ubuntu
26.04 CI replica with real podman 5.7 installed** (4.3s; LF and CRLF trees).
Published → CI green on both jobs. Live previews (8001/8081) restarted on the
new code.

All five roadmap phases remain COMPLETE, and the three open next-steps from the
previous handoff are **done**:

1. ✅ **Real sandbox execution** — `src/sandbox_engine/backends.py`:
   `NullBackend` (original stub) / `PodmanBackend` / `PodmanBackend(runsc=True)` (gVisor),
   selected by `DAP_SANDBOX_RUNTIME=auto|podman|runsc|null` (auto = podman if on PATH).
   `--network none` on create; every backend op fails-soft → sandbox parks in ERROR
   (fixed: the no-container branch now sets ERROR, not just returns False);
   failed create → registered with `container_id=None`, trackable/deletable.
   Runtime surfaced in `/health` + `/api/sandbox/status`. 12 new tests
   (`tests/test_sandbox_backends.py`, incl. a fake-podman end-to-end; that one
   test skips on Windows and runs on CI Linux).
2. ✅ **Production deployment** — `templates/docker/`: production `Dockerfile`
   (python:3.12-slim, non-root, healthcheck), `DOCKERCOMPOSE_PROD.yml`
   (postgres + api + dashboard + Caddy/Let's Encrypt; `docker compose config -q`
   validated), `Caddyfile` (`{$DAP_PUBLIC_HOST}`; /api+/ws+/docs → api:8001,
   default → dashboard:8081). `src/main.py` lifespan runs `init_db()` at startup.
   `docs/DEPLOYMENT_GUIDE.md` §0 documents the quick start. Ready to deploy the
   moment a host with a public domain exists.
3. ✅ **Real LLM metrics** — `LLMStats` registry in `src/agentic/llm.py`
   (records every `complete()` call); `/metrics` + `/metrics/summary` now emit
   real `dap_ai_tokens_total` / `dap_ai_requests_total` /
   `dap_ai_latency_seconds_*` (histogram buckets 0.1…60 + sum/count). Zero in
   keyless environments → the metrics determinism test is unaffected.
   5 new tests (`tests/test_llm_metrics.py`).
4. ✅ **Real auth persistence** — `users` table + `UserRepository` +
   `src/api/auth/credentials.py` (PBKDF2-HMAC-SHA256 600k iters, HS256 JWT pairs,
   15-min access / 7-day refresh with rotation; stdlib-only, zero new deps).
   `POST /auth/register` (first user = admin, 409 on duplicate), real login,
   `/auth/me` via Bearer. `DAP_AUTH_STRICT=1` = fail-closed (production compose
   sets it); dev default = fail-open (legacy mock tokens, all 13 legacy auth
   tests unchanged). 15 new tests (`tests/test_auth_users.py`).
5. ✅ **User-approved vault consistency pass** (see below).

- **Tests: 218/219 passing** (`TESTING=1 .venv/Scripts/python.exe -m pytest tests/ -q`;
  suite grew 187 → 219; the 1 skip is the Windows-only fake-podman test).
- **Do NOT run the suite without `TESTING=1`** — it targets asyncpg→localhost:5432
  (no PostgreSQL here) and fails with ConnectionRefused.
- `tests/conftest.py` forces the null sandbox runtime for the whole suite — the
  suite is environment-agnostic and never drives real podman even when it is
  installed (GitHub runners preinstall it). Don't remove that line (SOLUTION 34).
- **Published**: `https://github.com/mltmacster/devops-agentic-platform` (`origin/main`),
  CI = GitHub Actions pytest on 3.12/3.13 with `TESTING=1` (green on the CI-fix commit;
  the earlier red run 32764412039 on `3290e77` is explained by the podman auto-detect bug above).
- **Live processes (intentionally kept for user preview, venv python):** DAP API on
  **8001** (`server.log`), dashboard on **8081** (`dashboard.log`).
  `run_computing.sh cleanup` kills them — clean caches manually (`.pytest_cache`,
  `__pycache__`). Both were restarted after the code changes and live-verified
  (`/health` reports `sandbox_runtime`, `/auth/register` works, `/metrics` real AI values).

## Vault consistency pass (user item — all versioned, nothing deleted)

- `VAULT_DEPLOYMENT.yaml` **v1 retired** → `.vault/archive/2026-08-24_vault-deployment-v1/`
  (byte-identical to the pre-change snapshot copy; RETIREMENT.md with RCA + mitigations).
  **v2.0.0** written: valid YAML (`yaml.safe_load` ✓), version header explaining the
  replacement, current phases (all 5 complete), current pipeline, structured
  `next_goals`, checklist as plain text (no checkbox syntax in YAML).
- Versioned fixes (each with a version header naming what changed + where v1 lives):
  `VAULT_COORDINATOR.yaml` v1.1 (scope/date typos, rules aligned to actual practice),
  `VAULT_CONFIG.yaml` v1.1 (git-tracking comment, archive/snapshot schemas),
  `ARCHITECTURE.md` v1.1 (stale `.bak` ref removed, current state = reality),
  `.gitkeep-README.md` v1.1 (solution count 15 → 33, `bash` for the validator,
  `mv` not `cp` for archival), `scripts/validate_vault.sh` v1.1
  (`.vault/.vault` path fix, interpreter auto-detect, `VAULT_DEPLOYMENT.yaml`
  added to REQUIRED_FILES). `bash .vault/scripts/validate_vault.sh` → **passed**.
- `SOLUTIONS.md` grew 27 → **33** (Solutions 28–33: the vault pass, the validator,
  the JWT-`str`-secret bug, the ERROR-parking bug, the async-autouse-fixture rule,
  the uninitialized-DB auth degradation).
- Pre-change copies of all 33 touched files: `.vault/snapshots/2026-08-24-production/`.
- AGENTS.md now carries rule 6: vault **schema** files change only with explicit
  user approval, and every change must carry a version header.

## Goal of next session

1. **First real production deploy** — the only remaining piece of "production
   readiness": a host with a public domain. `cp .env.template .env`, set
   `DAP_JWT_SECRET`/`POSTGRES_PASSWORD`/`DAP_PUBLIC_HOST`, then
   `cd templates/docker && docker compose -f DOCKERCOMPOSE_PROD.yml up -d --build`,
   then `POST /api/auth/register` (first user = admin). Full quick start is in
   `docs/DEPLOYMENT_GUIDE.md` §0.
2. **Live sandbox verification on a podman host** — set `DAP_SANDBOX_RUNTIME=auto`
   (or `runsc`) and exercise create/start/stop/suspend/delete end-to-end against
   real containers; the unit layer is proven with the fake-podman test (CI).
   The state-tolerant suspend/resume (SOLUTION 36) is new since the production
   build — verify it live before trusting it on a real host.
3. **Optional** — RBAC integration tests (role-gated routes, not just the
   `/auth/check` evaluator); OTel/Jaeger tracing; rate limiting & quotas.

## Environment gotchas (Windows / Git Bash)

- `python` = Python 3.14.6 (C:\Python314, has PyYAML); `python3` = **Microsoft Store
  stub** that fails. Prefer the **venv**: `.venv/Scripts/python.exe` (canonical).
  `py -3.13` exists if a 3.13 repro is ever needed (CI covers 3.12/3.13).
- Git Bash: `pgrep`/`wmic`/`free`/`ss`/`rev` do NOT exist. `taskkill /PID` must be
  written `taskkill //PID`. PowerShell output is CRLF — strip `\r`. Heredocs decode
  via cp1252 — **box-drawing chars in heredoc Python get mangled**; use pure-ASCII
  anchors or `PYTHONUTF8=1`. Very long heredocs truncate — use `edit_file_tool`.
- `df -h /` label contains spaces — never parse by column index from the left.
- `edit_file_tool` refused files that hadn't been `read_file_lines`-ed first (read
  before write); its JSON-escaping quirk with nested quotes persists — workaround =
  byte-level Python replace via shell.
- `run_computing.sh cleanup` kills the two intentionally-live preview servers —
  when the user's preview must stay up, clean caches manually instead.
- **pytest-asyncio 1.4 strict mode**: never write async **autouse** fixtures —
  core pytest errors on any *sync* test that receives one (SOLUTION 32). Reset
  shared DB state per-test, inline, in async tests only.
- Project files use CRLF line endings; keep it that way (git `core.autocrlf=false`).
  Full-file rewrites via `replace_file` emit LF — harmless, or convert back to CRLF.
- No root `docker-compose.yml` (dev stack: `templates/docker/DOCKERCOMPOSE_FULL.yml`;
  prod stack: `templates/docker/DOCKERCOMPOSE_PROD.yml`).
- `.claude.json` is actually **markdown** despite the name — don't JSON-parse it.
- `dap_test.db` is the shared test SQLite DB (gitignored); stale copies gain tables
  over time — auth lookups tolerate a missing `users` table (SOLUTION 33).

## Documentation map (authoritative)

- `AGENTS.md` — vault rules (incl. rule 6: versioned schema changes; rule 7: env-agnostic
  test suite), compute-automation protocol, current root tree, phase status, session notes
  (latest: 2026-08-24 CI fix)
- `.vault/VAULT_OVERVIEW.md` — architecture diagram, service status matrix (219 tests),
  phase sections, **Production Deployment** section, open TODOs
- `.vault/SOLUTIONS.md` — 36 documented solutions (latest: Solutions 34–36, this session)
- `.vault/SNAPSHOT_LOG.md` — snapshot history (latest: 2026-08-24 17:19 CI-FIX entry)
- `.vault/VAULT_DEPLOYMENT.yaml` — v2.0.0 roadmap/pipeline (v1 in archive/ with RETIREMENT.md)
- `docs/DEPLOYMENT_GUIDE.md` — §0 production quick start (compose + Caddy), then the
  idealized k8s scale-out design (sections 1–4)
- `docs/ARTIFACT_STATUS_DASHBOARD.md` — v0.1.0 planning dashboard (banner marks it
  partially stale; header stamped per session)
- `docs/SSSESSION_HANDOFF_PROTOCOL.md` — session handoff protocol
- `.env.template` — full env reference (LLM, auth, DB, sandbox runtime, dashboard, TLS)
