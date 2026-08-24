# =============================================
# 🏛️ PROJECT VAULT — DO NOT MODIFY BY AGENTS
# =============================================

> **Version: 1.1 — 2026-08-24 consistency pass (user-approved).**
> v1 (2026-08-21) is preserved in `.vault/snapshots/2026-08-24-production/vault/`.
> Changes: removed stale `ARCHITECTURE.md.bak` reference, updated the directory
> tree to the actual layout, current-state section now matches the codebase
> (all phases complete, 219 tests), snapshot/solution examples aligned to
> actual practice (`YYYY-MM-DD-<name>/` dirs, single-file SOLUTIONS.md).

**WARNING:** This directory is the project's official knowledge repository.
Agents and automation systems MUST NOT:
- Delete files in this directory
- Remove or modify existing entries without explicit human approval
- Auto-purge old content

This vault is maintained for:
1. **UI/UX Preview** — Screenshots, dashboard exports, code snapshots
2. **Debugging Solutions** — Documented troubleshooting with root cause analysis  
3. **Architecture History** — Design decisions, ADRs, Mermaid diagrams
4. **Script Library** — Reusable automation and debugging scripts
5. **Deprecated Components** — Retirement documentation with migration paths

---

## 📁 Directory Structure

```
.vault/
├── VAULT_CONFIG.yaml           # Schema definitions (v1.1)
├── VAULT_COORDINATOR.yaml      # Cross-cutting coordination rules (v1.1)
├── VAULT_DEPLOYMENT.yaml       # Roadmap & pipeline (v2.0.0; v1 archived 2026-08-24)
├── LIFECYCLE_PROTOCOL.md       # Artifact lifecycle rules
├── ARCHITECTURE.md             # Current architecture state (this file)
├── VAULT_OVERVIEW.md           # Architecture overview + service status matrix
├── SNAPSHOT_LOG.md             # Snapshot tracking
├── SOLUTIONS.md                # Single-file solution library (numbered entries)
├── archive/                    # Retired components, each with RETIREMENT.md
├── snapshots/                  # Pre-change file snapshots, YYYY-MM-DD-<name>/
├── designs/  docs/  metrics/   # Design docs, technical docs, benchmarks
└── scripts/  certs/  logs/     # run_computing.sh, validate_vault.sh, run_all_tests.sh
```

---

## 🔄 How to Add Artifacts

### 1. Code Snapshot (After Major Changes)
```yaml
# .vault/snapshots/YYYY-MM-DD-<name>/  (e.g. 2026-08-24-production/)
# Copy pre-change versions of every file you touch, preserving relative paths,
# then add an entry to SNAPSHOT_LOG.md.
```

### 2. Design Document (Architecture Change)  
```markdown
# .vault/designs/YYYY-MM-DD_<feature>.md

## Decision ID: ADR-XXX
### Problem: [what problem]
### Solution: [what we chose]
### Alternatives Considered: [what we rejected & why]
```

### 3. Troubleshooting Solution
```markdown
# .vault/SOLUTIONS.md — append as "## Solution <next-number>: <title>"

**Problem**: [what broke]
**Root Cause**: [why it broke]
**Solution**: [how to fix it]
**Verification**: [steps proving the fix — always required]
```

### 4. Deprecated Component
```markdown
# .vault/archive/YYYY-MM-DD_<component>/RETIREMENT.md

## Component: <name>
## Retired: <date>
## Reason: <why it was replaced>

### Migration Steps:
1. [step 1]
2. [step 2]

### Old Code Location: <path>
### New Code Location: <path>
```

---

## 📋 Current Architecture State (verified 2026-08-24 — all 219 tests passing)

### Services Implemented:
- ✅ Auth Service — RBAC engine + real persistence (users table, PBKDF2, HS256 JWT, `DAP_AUTH_STRICT` fail-closed mode) — **28 tests**
- ✅ Workspace Orchestrator — CRUD + deterministic list — **15 tests**
- ✅ Sandbox Lifecycle Manager — state machine + API — **15 API + 39 engine tests**
- ✅ Sandbox Execution Backends — null / Podman / gVisor (`DAP_SANDBOX_RUNTIME`), `--network none` — **12 tests**
- ✅ IDE Core — WebSocket `/ws/{session_id}` + LSP protocol + REST config — **11 tests**
- ✅ Observability Collector — Prometheus `/metrics` (real LLM token/latency counters), Grafana JSON, health — **28 + 5 metrics tests**
- ✅ Agentic AI Engine — 3 agents + orchestrator + opt-in LLM backend (`LLMStats`) — **24 + 22 tests**
- ✅ Network Edge — public routing, DNS config, SSL manager, URL formatter — **20 tests**

### Production Readiness (2026-08-24):
- `src/main.py` lifespan runs `init_db()` at startup (Postgres bootstrap)
- `templates/docker/` — production Dockerfile, `DOCKERCOMPOSE_PROD.yml` (postgres + api + dashboard + Caddy/Let's Encrypt), Caddyfile

### Pending (next):
- First real production deploy (needs a host with a public domain → Caddy TLS)
- Live podman sandbox verification on a runtime host
- Optional: distributed tracing (OTel/Jaeger), rate limiting & quotas
