# DevOps Agentic Development Platform — Docker Compose Reference

## Full Stack (Development)

```yaml
version: '3.8'

services:
  # =====================================================
  # API Gateway
  # =====================================================
  api-gateway:
    image: nginx:alpine
    ports: ["80:80"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro

  # =====================================================
  # Control Plane (FastAPI Microservices)
  # =====================================================

  auth-service:
    build: src/api/auth
    ports: ["8001:8001"]
    environment:
      - DATABASE_URL=postgresql://dap_user:${DB_PASSWORD:-changeme}@postgres-pgvector:5432/dap_db
      - REDIS_URL=redis://redis-cluster:6379/0

  workspace-orchestrator:
    build: src/api/workspace
    ports: ["8002:8002"]
    environment:
      - DATABASE_URL=postgresql://dap_user:${DB_PASSWORD:-changeme}@postgres-pgvector:5432/dap_db
      - REDIS_URL=redis://redis-cluster:6379/0

  sandbox-lifecycle:
    build: src/api/sandbox
    ports: ["8003:8003"]
    environment:
      - DATABASE_URL=postgresql://dap_user:${DB_PASSWORD:-changeme}@postgres-pgvector:5432/dap_db
      - REDIS_URL=redis://redis-cluster:6379/0

  agentic-engine:
    build: src/api/agentic
    ports: ["8004:8004"]
    environment:
      - DATABASE_URL=postgresql://dap_user:${DB_PASSWORD:-changeme}@postgres-pgvector:5432/dap_db
      - REDIS_URL=redis://redis-cluster:6379/0
      - OLLAMA_API_URL=http://ollama:11434

  observability-collector:
    build: src/api/observability
    ports: ["8005:8005"]

  dashboard-api:
    build: src/api/dashboard
    ports: ["8006:8006"]

  # =====================================================
  # Data Plane (Shared Services)
  # =====================================================

  postgres-pgvector:
    image: pgvector/pgvector:0.8.0
    environment:
      POSTGRES_DB: dap_db
      POSTGRES_USER: dap_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]

  redis-cluster:
    image: redis:7-alpine
    command: --cluster-enabled yes
    ports: ["6379:6379"]

  minio:
    image: minio/minio:latest
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    ports: ["9000:9000"]

  # =====================================================
  # Lite VM Pool (Managed by sandbox-engine)
  # =====================================================

  vm-pool:
    image: gvisor/gvisor-linux:latest
    # Managed dynamically by sandbox lifecycle manager

  # =====================================================
  # Observability Stack (Grafana + Prometheus)
  # =====================================================

  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}

  # =====================================================
  # IDE Runtime (WebSocket Bridge)
  # =====================================================

  ide-bridge:
    build: src/ide-core
    ports: ["9000:9000"]

  # =====================================================
  # Agentic AI — Local LLM & Tools
  # =====================================================

  ollama:
    image: llama.cpp/ollama
    ports: ["11434:11434"]

  # =====================================================
  # Frontend (React Dashboard)
  # =====================================================

  web-dashboard:
    build: ./web/
    ports: ["3001:3001"]

volumes:
  pgdata:
```

## Environment Variables (`.env`)

```bash
# Database
DB_PASSWORD=your_secure_password_here

# MinIO
MINIO_PASSWORD=minio_secret

# Grafana
GRAFANA_PASSWORD=grafana_admin_password

# Ollama (optional: set model to pull)
OLLAMA_MODEL=codeLlama-7b-instruct
```

## Quick Start

```bash
# 1. Clone & setup
git clone <repo> && cd devops-agentic-platform

# 2. Create virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start full stack (Docker Compose)
docker compose up -d

# Check status
docker compose ps

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

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana Dashboard | `http://localhost:3001` | Metrics, monitoring |
| Admin Panel | `http://localhost:8006` | Platform management (GA only) |
| Web Dashboard | `http://localhost:3001` | User-facing dashboard (React) |
| Auth Service | `http://localhost:8001` | OAuth2/OIDC authentication, JWT tokens |
| Workspace API | `http://localhost:8002` | Workspace lifecycle management |
| Sandbox API | `http://localhost:8003` | VM boot/shutdown/suspend/resume operations |
| Agentic AI API | `http://localhost:8004` | Tool execution, agent orchestration |
| IDE Bridge | `http://localhost:9000` | Embedded IDE WebSocket connection |
| MinIO | `http://localhost:9000` | Object storage (artifacts, builds) |
| PostgreSQL + pgVector | `http://localhost:5432` | Database, semantic search |
| Redis Cluster | `http://localhost:6379` | Session store, caching |
| Ollama API | `http://localhost:11434` | Local LLM inference |
