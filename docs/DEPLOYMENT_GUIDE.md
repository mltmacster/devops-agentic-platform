# DevOps Agentic Development Platform — Deployment Guide

> **What is actually deployable today (2026-08-24):** the single-image compose
> stack in `templates/docker/` (Postgres + API + dashboard + Caddy/Let's Encrypt).
> The Kubernetes multi-cluster design in sections 2–4 below remains the
> idealized scale-out target. Use the quick start below for a real deployment.

## 0. Production Quick Start (compose stack — the current reality)

```bash
# 1. One-time host setup: Docker + compose; point your domain at the host
#    (A/AAAA record — Caddy provisions Let's Encrypt via the HTTP-01 challenge)

# 2. Configure (from the repo root)
cp .env.template .env
# Edit .env — required: DAP_JWT_SECRET, POSTGRES_PASSWORD, DAP_PUBLIC_HOST

# 3. Build & start
cd templates/docker
docker compose -f DOCKERCOMPOSE_PROD.yml up -d --build

# 4. Verify
curl https://YOUR-HOST/api/health        # {"status":"healthy",...,"sandbox_runtime":"..."}
curl https://YOUR-HOST/api/observability/metrics
curl -fsS https://YOUR-HOST/            # live dashboard (Caddy default route)
docker compose -f DOCKERCOMPOSE_PROD.yml ps
```

Service map: `caddy:80/443` → `/api/*`, `/ws/*`, `/docs` → `api:8001`;
everything else → `dashboard:8081` (which polls the API internally via
`DAP_API_URL=http://api:8001`). Auth runs **strict** (`DAP_AUTH_STRICT=1`):
register the first user (`POST /api/auth/register` — becomes admin), then log in;
all other routes require the signed JWT. The API container runs `init_db()` at
startup, so the Postgres schema is created automatically on first boot.

The per-service `DOCKERCOMPOSE_FULL.yml` remains for local development
(Postgres/Redis/Keycloak + pgVector). TLS: Caddy manages certificates
automatically — no manual Let's Encrypt steps, no separate NGINX/ALB required
for the first deployment.

## 1. Environment Setup

### Prerequisites
- Docker & Docker Compose (for development)
- Kubernetes cluster (for production)
- PostgreSQL 16 with pgVector 0.8.0 extension
- Redis Cluster
- Keycloak or Auth0 (for OIDC)

### Development Environment
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
cp .env.example .env
# Edit with your credentials

# 3. Start full stack
docker compose up -d

# Check status
docker compose ps
```

### Production Environment (Kubernetes)
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
        - name: auth-service
          image: dap/auth-service:latest
          ports:
            - containerPort: 8001
          envFrom:
            - secretRef:
                name: dap-secrets
```

## 2. Cluster Architecture

### Multi-Cluster Setup (Active-Active)
```mermaid
graph TB
    subgraph "US-East Cluster"
        A[API Gateway] --> B[Auth Service (3 replicas)]
        A --> C[Workspace Orchestrator (2 replicas)]
        A --> D[Sandbox Lifecycle Manager (2 replicas)]
        A --> E[Agentic AI Engine (4 replicas)]
    end
    
    subgraph "EU-West Cluster"
        F[API Gateway] --> G[Auth Service (3 replicas)]
        F --> H[Workspace Orchestrator (2 replicas)]
        F --> I[Sandbox Lifecycle Manager (2 replicas)]
        F --> J[Agentic AI Engine (4 replicas)]
    end
    
    subgraph "Shared Services"
        K[(PostgreSQL + pgVector)] --> A
        K --> F
        L[(Redis Cluster)] --> B & G
    end
    
    A --> K & L
    F --> K & L
