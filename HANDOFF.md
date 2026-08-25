# Handoff — DAP (DevOps Agentic Platform)

Project root: `C:\Users\mltma\Downloads\test\devops-agentic-platform`
Last session: **2026-08-25 — live podman verify 30/30 + production deploy prep**
(replaces prior handoff; previous: CI red→green, Solutions 34–36)

## Where things stand

**Goal 1 — live podman sandbox verification: ✅ DONE (30/30).**
The engine-wiring fix from the prior session (SOLUTION 37: API now drives the
execution backend via `execute_op` + persisted `container_id`) was verified
against real podman 5.7.0 in WSL Ubuntu 26.04 with
`dev-scripts/live_verify_sandbox.sh` — full lifecycle, drift→502, and
API-restart durability all green.

**Goal 2 — first real production deploy: ✅ ready, ⏸ awaiting your host + domain.**
The compose stack (`templates/docker/DOCKERCOMPOSE_PROD.yml`) was run end-to-end
for the first time (Docker Desktop, `DAP_PUBLIC_HOST=localhost`). Every blocker
found was fixed and re-verified (SOLUTIONS 38–39):
- build context, image healthcheck (`/health`), Caddyfile `/health*` route
- dashboard: valid browser JS + same-origin fetches (`DAP_BROWSER_API_URL`)
- 8001/8081 no longer published — Caddy (80/443) is the only public surface
- **new strict-mode route guard** (`src/api/auth/route_guard.py`): anonymous
  data-route access is 401 in production; registration closes after the first
  user (kills the first-user-admin race); the dashboard keeps working
- `init_db` migration (re-adds `container_id` on old Postgres schemas) verified

## What you need to do to deploy (10 minutes on the host)

```bash
# on a Linux host with Docker + compose; your domain A/AAAA-recorded to it
git clone https://github.com/mltmacster/devops-agentic-platform && cd devops-agentic-platform
cp .env.template templates/docker/.env
# edit templates/docker/.env:
#   DAP_JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
#   POSTGRES_PASSWORD=<random>
#   DAP_PUBLIC_HOST=<your-domain>
cd templates/docker
docker compose -f DOCKERCOMPOSE_PROD.yml up -d --build
curl https://<your-domain>/health
```
Then register the admin immediately (`POST /api/auth/auth/register` — first
user; registration is closed afterwards). Full details:
`docs/DEPLOYMENT_GUIDE.md` §0.

**Known first-deploy limitation**: sandbox execution inside the api container
is the no-op null backend (`auto` finds no podman in the image). Records +
state machine work; real containers don't run in pure-compose mode. See
`docs/DEPLOYMENT_GUIDE.md` §0 "Real sandbox execution in production" for the
two opt-in paths (host podman socket, or API natively on the host).

## User preferences & constraints (carry forward)

- Vault rules (AGENTS.md): never delete `.vault/` without approval; snapshot
  before >50-line changes (this session: `.vault/snapshots/2026-08-25-deploy-prep/`);
  fixes → SOLUTIONS.md (now at 39); trace to commits; schema YAML only with
  explicit approval + version headers.
- Test suite must stay environment-agnostic (`tests/conftest.py` pins null
  runtime; the route guard is a no-op in dev mode).
- **Do NOT run `run_computing.sh cleanup`** — it kills the intentionally-live
  previews (8001 API / 8081 dashboard, Windows venv python); clean
  `.pytest_cache` / `__pycache__` / `dap_test.db` manually.
- CRLF repo convention (`core.autocrlf=false`) — bash scripts must be LF.
- Commit + push after verified work (repo `main` →
  `https://github.com/mltmacster/devops-agentic-platform`).
- Windows: use `.venv/Scripts/python.exe` (3.14.6); long compound commands
  get mangled through `wsl … bash -lc '…'` from Git Bash — write script files
  instead.

## This session's changes (all in the repo)

| Area | Change |
|---|---|
| `templates/docker/DOCKERCOMPOSE_PROD.yml` | context `../..`; 8001/8081 unpublished; commented podman-socket option; `DAP_BROWSER_API_URL` |
| `templates/docker/Dockerfile` | healthcheck `/api/health` → `/health` |
| `templates/docker/Caddyfile` | `handle /health*` → api |
| `dap_dashboard.py` | `__DAP_BROWSER_API__` sentinel + `DAP_BROWSER_API_URL` (defaults to `DAP_API_URL`) |
| `docs/DEPLOYMENT_GUIDE.md` | §0 rewritten: `.env` placement, Caddy-only exposure, prod sandbox-execution options, dry-run status |
| `src/api/auth/route_guard.py` | NEW `StrictAuthMiddleware` (strict-mode fail-closed) |
| `src/api/auth/main.py` | registration 403 once any user exists (strict) |
| `src/main.py` | guard registered (CORS outermost) |
| `tests/test_route_guard.py` | NEW — 8 tests |
| `.vault/*` | Solutions 37–39, snapshot log, overview, metrics, AGENTS notes |

Prior-session (uncommitted) changes carried in the same commit:
`src/api/sandbox/main.py` (engine wiring), `src/sandbox_engine/*`
(`execute_op`, `TIERS`, `--pull missing`), `src/database/*`
(`container_id` + migration), `tests/fake_backends.py`,
`dev-scripts/live_verify_sandbox.sh`.

**Tests: 237 passed / 1 skipped** (Windows venv 3.14.6) · **live verify 30/30** (WSL)
