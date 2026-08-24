# =============================================
# DevOps Agentic Development Platform (DAP)
# =============================================

## Project Overview
A multi-tenant SaaS coding sandbox on a custom Lite VM + Lite Linux Ubuntu OS, with an embedded Lite IDE and agentic AI coding assistants.

**Stack:** Python/FastAPI, Monaco IDE, Podman/gVisor sandboxes, pgVector 0.8.0, Ollama, LangGraph

**Deployment:** Docker Compose (dev) → Kubernetes + Istio (prod)

---

## Quick Start

### Prerequisites
- Docker & Docker Compose 2.0+
- Podman (for sandboxing)
- pgvector 0.8.0 extension installed on PostgreSQL 15+

### Local Development
```bash
git clone https://github.com/yourorg/devops-agentic-platform.git
cd devops-agentic-platform

# Clone and start the full development stack
docker compose up -d

# Verify services are running
curl http://localhost:8000/healthz
```

### Environment Variables
See `.env.example` for all required configuration. Copy and configure:
```bash
cp .env.example .env.local
# Edit .env.local for your configuration
```

---

## Architecture Overview

### Service Components
| Service | Port | Purpose |
|---------|------|---------|
| API Gateway | 8000 | Request routing, rate limiting, auth validation |
| Auth Service | 8001 | OAuth2/JWT, RBAC enforcement, session management |
| Workspace Service | 8002 | Sandbox provisioning, project management, Git integration |
| IDE Service | 8003 | Monaco Editor WebSocket gateway, LSP proxy |
| Agentic AI Engine | 8004 | Multi-agent orchestration, LangGraph workflows |
| Observability Service | 8005 | Metrics collection, Prometheus/Grafana integration |

### Data Stores
| Store | Purpose | Connection |
|-------|---------|------------|
| PostgreSQL + pgVector 0.8.0 | Primary database, semantic search | postgresql://localhost:5432/dap
| Redis | Session cache, rate limiting, message queues | redis://localhost:6379
| MinIO | Code artifacts, build outputs, logs | http://localhost:9000
| Ollama | Local LLM inference (code, research) | http://localhost:11434

---

## Development Workflow

### Directory Structure
```
├── src/                        # Application source code
│   ├── api/                  # FastAPI services
│   │   ├── auth/             # Authentication & RBAC
│   │   ├── workspace/        # Sandbox orchestration
│   │   ├── ide/              # Monaco Editor integration
│   │   └── observability/    # Metrics & monitoring
│   ├── sandbox-engine/       # VM lifecycle management
│   └── agentic/              # AI engine & agents
├── templates/                # Infrastructure & config templates
│   ├── api/                  # OpenAPI specs, schemas
│   ├── docker/               # Dockerfile templates
│   ├── kubernetes/           # K8s manifests, Helm charts
│   ├── github-actions/       # CI/CD workflows
│   └── scripts/              # Dev automation scripts
├── tests/                    # Test suites (unit, integration, e2e)
└── docs/                     # Documentation
```

### Service Development Pattern
Each microservice follows this structure:
1. Define Pydantic models for request/response schemas
2. Create endpoint handlers with proper error handling
3. Add middleware (auth, rate limiting, logging)
4. Write unit tests with pytest + responses
5. Add integration tests with Testcontainers

---

## Key Concepts

### RBAC Hierarchy
```
GA (Global Admin) ──> Platform management, all teams
    ↓
Team Admin ───────> Team-specific admin, sandbox creation
    ↓
Developer ─────────> Personal workspace access
    ↓
Read-Only ────────> Read-only documentation/access
```

### Sandbox Architecture
1. **Podman** — Creates isolated containers with user namespaces
2. **gVisor** — User-space kernel, minimal attack surface
3. **Cilium eBPF** — Zero-trust network policies, pod-level isolation
4. **Resource Limits** — CPU, memory, disk quotas per sandbox

---

## Contributing Guidelines
1. All code must have comprehensive docstrings (Google style)
2. Tests required for all new endpoints (>80% coverage target)
3. Architecture decisions documented in ADRs under `docs/adr/`
4. All security changes require threat model updates in `docs/security-design.md`
