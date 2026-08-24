# DevOps Agentic Development Platform — Architecture Reference

## Core Components Summary

### Control Plane (FastAPI Microservices)
| Service | Port | Protocol | Responsibility |
|---------|------|----------|----------------|
| Auth Service | 8001 | gRPC + REST | IAM, RBAC, session management, SSO (OAuth2/OIDC) |
| Workspace Orchestrator | 8002 | gRPC + REST | Tenant provisioning, workspace lifecycle, quota enforcement |
| Sandbox Lifecycle Manager | 8003 | gRPC + REST | VM boot/shutdown, container orchestration, resource allocation |
| Agentic AI Engine | 8004 | WebSocket + REST | Tool execution, agent orchestration, code completion API |
| Observability Collector | 8005 | gRPC + OTLP | Metrics, logs, traces aggregation → Prometheus/Grafana |
| Dashboard API | 8006 | GraphQL + REST | Admin panel, user panels, metrics visualization |

### Data Plane (Shared Infrastructure)
| Component | Technology | Purpose |
|-----------|------------|---------|
| Lite VM | Ubuntu 24.04 + Podman / gVisor | Isolated coding sandbox with full Linux environment |
| Network Policy | Cilium / Calico | Zero-trust, per-tenant network isolation |
| Object Storage | MinIO / S3 | Code artifacts, builds, container images |
| Vector DB | PostgreSQL + pgVector 0.8.0 | Code search, semantic retrieval, RAG context |
| ML Extensions | pgML + pgGraph | On-demand ML inference, graph analytics in-code |
| Session Store | Redis Cluster | Session state, agent context, rate limiting |

### Embedded IDE Layer
| Component | Tech | Purpose |
|-----------|------|---------|
| Editor Core | Monaco Editor / VS Code Web | Multi-language editing, LSP integration |
| WebSocket Bridge | ws + Node.js | Real-time file sync, LSP communication |
| Terminal Emulator | xterm.js + webtty | Sandboxed shell access within IDE |
| LSP Provider | Language Server Protocol | Syntax highlighting, code completion, diagnostics |
| Git Integration | gitea / GitLab API + native git | Version control, PR workflows |

## Security Architecture

### IAM
- OAuth2/OIDC authentication via Keycloak/Auth0
- JWT access tokens + Redis session store
- MFA enforcement (TOTP, WebAuthn)

### RBAC
Role Hierarchy: GA > Team Admin > Developer > Read-Only

| Action | GA | Team Admin | Developer | Read-Only |
|--------|----:|-----------:|----------:|---------:|
| Create Workspace | ✅ | ✅ (own team) | ❌ | ❌ |
| Create Sandbox | ✅ | ✅ | ✅ (own sandbox) | ❌ |
| Delete Sandbox | ✅ | ✅ (own team) | ✅ (own sandbox) | ❌ |
| Execute Agentic AI | ✅ | ✅ | ✅ | ❌ |
| Modify Network Policy | ✅ | ❌ | ❌ | ❌ |

### Zero-Trust Network
Allowed Egress (Whitelist):
- DNS resolution: 10.96.0.2:53 (DNS)
- Package registries: pypi.org, crates.io, registry.npmjs.com (443)
- API services: api.github.com, oai.openai.com (443)
- Ollama server: 127.0.0.1 (11434)

All other outbound traffic: BLOCKED
All inbound TCP: BLOCKED (only IDE WebSocket + API Gateway allowed)

## Agentic AI Engine

### Agent Types
| Agent | Responsibility | Tools Used |
|-------|---------------|------------|
| Code Architect | Plans scaffolding, generates boilerplate | Git tools, file operations |
| Debugger | Traces errors, suggests fixes | Stack trace analysis, code search |
| Test Generator | Writes unit/integration tests | Source analysis, framework detection |
| Researcher | Web research, doc fetching | Crawle4AI, IBM Docling |
| Documentation | Generates API docs from code | Docling, LSP introspection |

### Tool Provider Registry
| Category | Tools |
|----------|-------|
| Git Operations | commit, push, diff, branch management |
| Web Research | Crawle4AI for website scraping |
| Document Processing | IBM Docling (PDF/Word → structured text) |
| Agentic Workflows | LangGraph (graph-based multi-agent orchestration) |
| Local LLM Inference | Ollama |
| Semantic Search | pgVector 0.8.0 |

## Observability

### Metrics Collection
| Source | Exporter | Destination |
|--------|----------|-------------|
| Sandbox Telemetry | Prometheus Node Exporter | Prometheus |
| Agentic AI Logs | Fluentd/Logstash | Loki / Elasticsearch |
| Application Traces | Jaeger/OTLP | Jaeger |
| IDE Telemetry | Prometheus custom exporter | Prometheus |

### Key Metrics by Layer
| Layer | Critical Metrics | Alerts Thresholds |
|-------|-----------------|-------------------|
| Platform | CPU, RAM, Disk I/O, Network Throughput | 90% sustained for 5 min → WARN; 95% → CRITICAL |
| Sandbox | VM Uptime, Boot Time, Disk Quota Usage | >10 sec boot → WARN; 80% disk → WARN |
| Agentic AI | Token Usage, Latency (P50/P95), Error Rate | >2s P95 → WARN; >5% errors → CRITICAL |
| IDE | Active Sessions, LSP Latency, Memory Usage | >500ms LSP → WARN; OOM → CRITICAL |
| Security | Failed Auth, Anomalous Egress, RBAC Violations | Any violation → CRITICAL |

## Deployment Topology

### Development (Docker Compose)
services:
- auth-service (8001)
- workspace-orchestrator (8002)
- sandbox-lifecycle (8003)
- agentic-engine (8004)
- observability-collector (8005)
- dashboard-api (8006)
- postgres-pgvector: pgvector/pgvector:0.8.0
- redis-cluster: redis:7-alpine (cluster mode)
- minio: minio/minio:latest
- vm-pool: gvisor/gvisor-linux:latest
- prometheus: prom/prometheus:latest
- grafana: grafana/grafana:latest (3001)
- ide-bridge: ide-bridge (9000)
- ollama: llama.cpp/ollama (11434)
- web-dashboard: React frontend (3001)

### Production (Kubernetes)
- Namespaced per environment (staging, prod)
- Ingress controller for external traffic
- Istio service mesh for mTLS + observability
- Prometheus Operator for metrics collection

## Security Controls Summary

### IAM & RBAC
- OAuth2/OIDC authentication via Keycloak/Auth0
- JWT access tokens with Redis session cache
- MFA enforcement for privileged actions (TOTP, WebAuthn)
- RBAC: GA > Team Admin > Developer > Read-Only

### Network Security
- Zero-trust via Cilium eBPF enforcement
- Whitelist-only outbound (GitHub, PyPI, crates.io, etc.)
- Ingress restricted to IDE WebSocket + API Gateway only

### Sandbox Isolation
- User namespace mapping (root → unprivileged host user)
- overlayfs for immutable base + bind mounts for /home, /root
- Podman/gVisor as virtualizer

## Plugin Architecture

### Plugin Interface (plugin_interface.py)
class BasePlugin(ABC):
    name: str = "base"
    version: str = "1.0.0"

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool: ...

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def health_check(self) -> Dict[str, Any]: ...


class StackModule(BasePlugin):
    required_tools: List[str] = []

    @abstractmethod
    def provision(self, sandbox_id: str) -> bool: ...


### Available Stacks (Plugs)
| Stack | Runtime | Tools | Database | AI/ML |
|-------|---------|-------|----------|-------|
| Python | 3.12 + pip | FastAPI, uvicorn | SQLite | Ollama, LangGraph |
| Rust | 1.70+ + cargo | Actix-web | SQLite | — |
| Node.js | 20.x + npm/yarn | React, Express | SQLite | — |
| ML/Data | Python | pgVector 0.8.0, Ollama | PostgreSQL + pgML | LangGraph |
| Full Web | Node 20 + React | Vite, Tailwind | PostgreSQL (hosted) | pgML, pgGraph |

### Plugin Discovery
1. Built-in: Shipped with the platform (src/agentic/plugins/)
2. Community: ~/.dap/plugins/ (discoverable by name)
3. Enterprise: Signed, custom paths (/etc/dap/plugins/)

## Quick Start (Development)
Command line:
  git clone <repo> && cd devops-agentic-platform
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  docker compose up -d
  open http://localhost:3001   # Grafana/Grafana UI

curl -X POST http://localhost:8002/workspaces \
  -H "Authorization: Bearer <token>" \
  -d '{"name": "my-workspace", "tier": "pro"}'
