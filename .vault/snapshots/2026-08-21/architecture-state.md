# =============================================
# VAULT SNAPSHOT — 2026-08-21 (Today)
# =============================================

## Architecture State Snapshot
**Date**: 2026-08-21  
**Source**: AGENTS.md (current version)

### Service Stack
```
┌───────────────────────┐     ┌──────────────────┐
│    Client Layer       │     │  Edge & Gateway   │
│ Browser / VS Code Ext│────▶│ WAF + API GW     │
└───────────────────────┘     └────────┬─────────┘
                                      │
                    ┌───────────────▼───────────────┐
                    │  Control Plane (FastAPI)      │
                    ├───────────────┬───────────────┤
                    │ Auth Service  │ Workspace     │
                    │ (IAM/RBAC)    │ Orchestrator  │
                    ├───────────────┤───────────────┤
                    │ Sandbox LM    │ Agentic AI    │
                    │ (VM lifecycle)│ Engine        │
                    ├───────────────┤───────────────┤
                    │ Observability │ Dashboard     │
                    │ Collector     │ API           │
                    └───────────────┴───────────────┘
                                      │
                    ┌───────────────▼───────────────┐
                    │  Data Plane (Shared Services)   │
                    ├───────────────┬───────────────┤
                    │ Lite VM Pool  │ Redis Cluster   │
                    │ (Ubuntu 24.04)│ PostgreSQL +    │
                    └───────────────┤ pgVector 0.8.0  │
```

### Key Metrics (Test Results)
| Service | Tests Run | Passed | Failure Rate |
|---------|-----------|--------|-------------|
| Auth API | 13 | 13 | 0% ✅ |
| Workspace API | 11 | 11 | 0% ✅ |
| Sandbox API | 11 | 11 | 0% ✅ |

### File Counts
```
src/api/auth/          : 3 files (~800 lines)
src/api/workspace/     : 1 file  (~245 lines)  
src/api/sandbox/       : 1 file  (~248 lines)
src/database/          : 3 files (~400 lines)
tests/                 : 2 test files (~685 lines)
```

### Open Issues
1. Auth service has stubbed login/refresh (no real auth provider)
2. No IDE WebSocket implementation yet  
3. No Prometheus/Grafana integration implemented
4. Agentic AI engine is just a skeleton
