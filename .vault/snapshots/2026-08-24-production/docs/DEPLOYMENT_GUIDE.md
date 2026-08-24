# DevOps Agentic Development Platform — Deployment Guide

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
