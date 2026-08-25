# Test Report — 2026-08-25 (live verify + deploy prep session)

## Suite (Windows, `.venv` Python 3.14.6, `TESTING=1`)
- **237 passed / 1 skipped in ~10s** (total 238; was 229 passed + 1 skipped before this session; +8 route-guard tests — the prior engine-wiring session added 11)
- New: `tests/test_route_guard.py` (8 tests — dev fail-open, strict 401s, token 200, allowlist, registration closure)
- Command: `TESTING=1 .venv/Scripts/python.exe -m pytest tests/ -q`

## Live verification (WSL Ubuntu 26.04, real podman 5.7.0)
- `dev-scripts/live_verify_sandbox.sh <repo> 8002` → **30/30 PASS, ALL GREEN**
- Covers: create/start/exec/`/sys/class/net`==lo/pause/resume/stop/
  suspend-from-stopped/resume-from-stopped/delete/drift-502/API-restart durability

## Production compose dry run (Docker Desktop 29.7.2, `DAP_PUBLIC_HOST=localhost`)
- Build: OK (python:3.12-slim base; shared api+dashboard image)
- Containers: postgres/api/dashboard/caddy — all running, api+dashboard healthy
- HTTPS via Caddy internal CA (localhost); 80→443 redirect
- Strict auth over the public path: anon 401 (data routes) · register 201 →
  403 closed · login 200/401 · `/me` admin · token 200
- Dashboard: 200, valid JS (`const DAP_API = ''` → same-origin fetches)
- Port exposure: api/dashboard `docker port` empty (Caddy-only) ✓
- Postgres persistence: workspace + JWT survive `docker restart api` ✓
- `init_db` migration: dropped `container_id` re-added on real PostgreSQL ✓
- Teardown: `docker compose down -v`, images removed, throwaway `.env` deleted

## Environment cleanup
- WSL: stray probe containers removed (`dap-fieldtest*`, 2 ad-hoc), `/tmp/tst.txt` removed; `~/.venv-dap-live` kept
- Windows: `.pytest_cache` / `__pycache__` / stale `dap_test.db` cleaned before commit; previews (8001/8081) untouched
