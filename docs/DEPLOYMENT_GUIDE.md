# DevOps Agentic Development Platform — Deployment Guide

> **What is actually deployable today (2026-08-25):** the single-image compose
> stack in `templates/docker/` (Postgres + API + dashboard + Caddy/Let's
> Encrypt), dry-run-verified end-to-end (build, strict auth, Postgres
> persistence, schema migration, Caddy TLS via internal CA for localhost).
> Sandbox execution inside the container is the no-op null backend unless you
> wire in the host podman (§0, "Real sandbox execution in production"). The
> Kubernetes multi-cluster design in sections 2–4 below remains the idealized
> scale-out target. Use the quick start below for a real deployment.

## 0. Production Quick Start (compose stack — the current reality)

```bash
# 1. One-time host setup: Docker + compose; point your domain at the host
#    (A/AAAA record — Caddy provisions Let's Encrypt via the HTTP-01 challenge)

# 2. Configure — the .env must sit NEXT TO THE COMPOSE FILE: docker compose
#    auto-loads .env from the project directory (templates/docker/), not the
#    repo root
cp .env.template templates/docker/.env
# Edit templates/docker/.env — required: DAP_JWT_SECRET, POSTGRES_PASSWORD,
# DAP_PUBLIC_HOST (your domain)

# 3. Build & start
cd templates/docker
docker compose -f DOCKERCOMPOSE_PROD.yml up -d --build

# 4. Verify
curl https://YOUR-HOST/health             # {"status":"healthy",...,"sandbox_runtime":"..."}
curl https://YOUR-HOST/api/observability/metrics
curl -fsS https://YOUR-HOST/            # live dashboard (Caddy default route)
docker compose -f DOCKERCOMPOSE_PROD.yml ps
```

Service map: `caddy:80/443` is the **only public entry point** — `/api/*`,
`/ws/*`, `/docs` → `api:8001`; everything else → `dashboard:8081`. The api
and dashboard ports are deliberately **not** published to the host (SOLUTION
38); use `docker compose logs` for debugging. The dashboard *page* fetches the
API same-origin (browser → Caddy → api) while the dashboard *process* talks
to the API over the compose network (`DAP_API_URL=http://api:8001`).

Auth runs **strict** (`DAP_AUTH_STRICT=1`): register the first user
(`POST /api/auth/register` — becomes admin), then log in; all other routes
require the signed JWT. The API container runs `init_db()` at startup, so the
Postgres schema is created automatically on first boot — and the lightweight
migrations (SOLUTION 37) upgrade schemas created by older releases.

### Real sandbox execution in production (optional — first-deploy note)

Inside the api container, `DAP_SANDBOX_RUNTIME=auto` finds no podman binary
and resolves to the **null backend**: sandbox records, tiers, and the full
state machine work, but no real container is created (the original no-op
stub). The live-verified podman path (`dev-scripts/live_verify_sandbox.sh`)
runs where podman *is* installed (e.g. the WSL runtime host). Two ways to get
real execution in production:

- **Option A — API natively on the host (recommended for a first deploy with
  real sandboxes).** Install podman (rootless) on the host, `python -m venv`
  + `pip install -r requirements.txt`, run uvicorn under systemd with
  `DAP_SANDBOX_RUNTIME=auto` and `DATABASE_URL` pointing at the compose
  postgres (publish 5432 for it), and `DAP_AUTH_STRICT=1`. The podman CLI
  drives real containers directly. Keep the compose stack for dashboard +
  Caddy + postgres.
- **Option B — everything in compose, via the host podman socket.** Rebuild
  the api image with a podman *remote* client, mount the host's rootless
  socket into the container, and set `DAP_SANDBOX_RUNTIME=podman` +
  `PODMAN_CONNECTION=sock` (a ready-to-uncomment block is in
  `DOCKERCOMPOSE_PROD.yml`).

Either way, the base image (`ubuntu:24.04`) is pulled on the host at most
once per fresh host (`--pull missing`).

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
