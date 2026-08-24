# DevOps Agentic Development Platform — Quick Reference Guide

## 🔗 Quick Links

| Resource | URL / Path | Purpose |
|----------|-----------|---------|
| Architecture Overview | `docs/01-architectural-overview.md` | System design, component map |
| Service Boundaries | `docs/02-service-boundaries.md` | Microservices, communication patterns |
| Security Controls | `docs/03-security-controls.md` | IAM, RBAC, GA, network policy |
| Sandbox Engine | `docs/04-sandbox-engine.md` | Lite VM architecture, resource limits |
| IDE Integration | `docs/05-ide-integration.md` | Monaco Editor, LSP, WebSocket protocol |
| Agentic AI Engine | `docs/06-agentic-engine.md` | Multi-agent architecture, tool registry |
| Observability | `docs/07-observability-dashboard.md` | Metrics, Grafana dashboards |
| API Reference | `docs/API_REFERENCE.md` | All HTTP endpoints, request/response examples |
| Plugin System | `docs/PLUGIN_SYSTEM.md` | Plugin interface, built-in stacks, dev guide |
| Security Design | `docs/SECURITY_DESIGN.md` | Threat model, mitigations |
| Docker Compose | `docs/DOCKER_COMPOSE_GUIDE.md` | Full stack orchestration, environment vars |
| Deployment Guide | `docs/DEPLOYMENT_GUIDE.md` | K8s, ECS, multi-cluster setup |
| Project Plan | `docs/PROJECT_PLAN.md` | 12-week development timeline, deliverables |
| Architecture Reference | `dev-scripts/ARCHITECTURE_REFERENCE.md` | Full reference (searchable) |

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Clone & setup
git clone <repo> && cd devops-agentic-platform

# 2. Create virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start full stack (Docker Compose)
docker compose up -d

# 5. Open dashboard
open http://localhost:3001   # Grafana/Grafana UI

# 6. Create first workspace
curl -X POST http://localhost:8002/workspaces \
  -H "Authorization: Bearer <token>" \
  -d '{"name": "my-workspace", "tier": "pro"}'

# 7. Create first sandbox
curl -X POST http://localhost:8003/sandboxes \
  -H "Authorization: Bearer <token>" \
  -d '{"workspace_id": "<your-workspace-id>", "stack": "python"}'

# 8. Run agentic AI
curl -X POST http://localhost:8004/agentic/run \
  -H "Authorization: Bearer <token>" \
  -d '{"sandbox_id": "<your-sandbox-id>", "query": "Build a REST API for a todo app using FastAPI"}'
```

## 📋 Available Ports

| Port | Service | Purpose |
|------|---------|---------|
| 80 | API Gateway (Nginx) | Reverse proxy, load balancing |
| 3001 | Grafana + Web Dashboard | Metrics, monitoring, user panel |
| 8001 | Auth Service | OAuth2/OIDC authentication, JWT tokens |
| 8002 | Workspace Orchestrator | Tenant/workspace lifecycle management |
| 8003 | Sandbox Lifecycle Manager | VM boot/shutdown/suspend/resume operations |
| 8004 | Agentic AI Engine | Tool execution, agent orchestration, code completion API |
| 8005 | Observability Collector | Metrics collection, log aggregation |
| 8006 | Dashboard API | Admin panel (GraphQL) |
| 9000 | IDE Bridge | Embedded IDE WebSocket connection |
| 9001 | MinIO | Object storage (artifacts, builds) |
| 5432 | PostgreSQL + pgVector | Database, semantic search |
| 6379 | Redis Cluster | Session store, caching |
| 11434 | Ollama | Local LLM inference |

## 🧪 Available Development Stacks

| Stack | Runtime | Tools | Database | AI/ML |
|-------|---------|-------|----------|-------|
| Python | 3.12 + pip | FastAPI, uvicorn, requests | SQLite | Ollama, LangGraph |
| Rust | 1.70+ + cargo | Actix-web, tokio | SQLite | — |
| Node.js | 20.x + npm/yarn | React, Express, Vite | SQLite | — |
| ML/Data | Python 3.12 + pip | pandas, numpy, scikit-learn | PostgreSQL + pgVector | Ollama, LangGraph |
| Full Web | Node 20 + React | Next.js, Tailwind CSS | PostgreSQL (hosted) | pgML, pgGraph |

## 🤖 Agentic AI Agents

| Agent | Trigger Keywords | Example Use Case |
|-------|-----------------|------------------|
| Code Architect | "build", "create", "generate" | "Build a REST API for a todo app" |
| Debug Agent | "debug", "fix", "error" | "Fix this NullPointerException in my code" |
| Test Generator | "write tests", "add unit test" | "Write unit tests for this function" |
| Researcher | "research", "find docs" | "Research how to implement rate limiting in FastAPI" |
| Documentation Agent | "document", "docs" | "Generate API documentation for my project" |

## 🔧 Troubleshooting

### Common Issues
| Problem | Solution |
|---------|----------|
| `docker compose up` fails | Check `.env` file, verify all credentials are set |
| Auth service returns 500 | Check PostgreSQL connection in `DATABASE_URL` env var |
| Sandbox fails to start | Verify `vm-pool` image is downloaded, check disk space |
| Agentic AI times out | Increase timeout in `agentic-engine` config, check Ollama API |
| IDE can't connect to sandbox | Verify WebSocket bridge port 9000 is open, check network policy |

### Useful Commands
```bash
# Check all services
docker compose ps

# View logs for a specific service
docker compose logs auth-service
docker compose logs sandbox-lifecycle

# View platform metrics
curl http://localhost:8005/metrics | grep sandbox

# Check sandbox status
curl -X GET http://localhost:8003/sandboxes/{id}/status

# Create a new sandbox
curl -X POST http://localhost:8003/sandboxes \
  -H "Authorization: Bearer <token>" \
  -d '{"workspace_id": "<id>", "stack": "python"}'

# Stop a sandbox
curl -X POST http://localhost:8003/sandboxes/{id}/stop

# Run agentic AI
curl -X POST http://localhost:8004/agentic/run \
  -H "Authorization: Bearer <token>" \
  -d '{"sandbox_id": "<id>", "query": "your request"}'
