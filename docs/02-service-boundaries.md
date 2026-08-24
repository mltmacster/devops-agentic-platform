# Service Boundaries — Microservices Architecture

## 1. Boundary Principles

This document defines the service boundaries for the DevOps Agentic Development Platform using domain-driven design (DDD) principles.

### Core Principles
1. **Bounded Contexts**: Each service owns its data and business logic — no shared databases
2. **Async Communication**: Services communicate via message queues (Kafka/RabbitMQ) for decoupling
3. **API Gateway Pattern**: Single entry point with rate limiting, auth delegation, and request routing
4. **Event Sourcing**: Critical state changes emitted as events for auditability

---

## 2. Service Map

| Service | Port | Protocol | Responsibility |
|---------|------|----------|----------------|
| Auth Service | 8001 | gRPC + REST | IAM, RBAC, session management, SSO (OAuth2/OIDC) |
| Workspace Orchestrator | 8002 | gRPC + REST | Tenant provisioning, workspace lifecycle, quota enforcement |
| Sandbox Lifecycle Manager | 8003 | gRPC + REST | VM boot/shutdown, container orchestration, resource allocation |
| Agentic AI Engine | 8004 | WebSocket + REST | Tool execution, agent orchestration, code completion API |
| Observability Collector | 8005 | gRPC + OTLP | Metrics, logs, traces aggregation → Prometheus/Grafana |
| Dashboard API | 8006 | GraphQL + REST | Admin panel, user panels, metrics visualization |

---

## 3. Service Definitions

### 3.1 Auth Service (`/auth`)
- **Port**: 8001 (gRPC) + 8001:REST
- **Protocol**: gRPC for internal, REST for public endpoints
- **Data Store**: PostgreSQL (users/roles), Redis (sessions)
- **Responsibilities**: OAuth2/OIDC auth flow, JWT token issuance/validation, RBAC policy evaluation

### 3.2 Workspace Orchestrator (`/workspace`)
- **Port**: 8002 (gRPC) + GraphQL for admin dashboard
- **Data Store**: PostgreSQL (workspaces/quotas), Redis (rate limits)
- **Responsibilities**: Tenant/workspace creation and lifecycle, quota enforcement

### 3.3 Sandbox Lifecycle Manager (`/sandbox`)
- **Port**: 8003 (gRPC) + WebSocket for live updates
- **Responsibilities**: VM boot/shutdown/suspend/resume, resource allocation enforcement

### 3.4 Agentic AI Engine (`/agentic`)
- **Port**: 8004 (REST) + WebSocket for streaming responses
- **Responsibilities**: Multi-agent orchestration, tool execution, LSP integration

### 3.5 Observability Collector (`/observability`)
- **Port**: 8005 (gRPC + OTLP)
- **Responsibilities**: Sandbox metrics, AI telemetry, IDE session metrics

### 3.6 Dashboard API (`/dashboard`)
- **Port**: 8006 (GraphQL) + 3001:REST
- **Responsibilities**: Admin panel with fleet-wide metrics, user panels showing personal sandbox status

---

## 4. Communication Patterns

| Scenario | Communication | Latency Requirement |
|----------|--------------|-------------------|
| User creates workspace | Sync (HTTP) | < 2s |
| Sandbox boot notification | Async (Kafka) | Best-effort |
| Agentic AI tool execution | Sync + Stream (WS) | < 5s first token |
| Sandbox resource metrics | Async (Prometheus) | 15s intervals |
| RBAC policy update | Sync (gRPC) + Cache | < 100ms |
| IDE file sync | Real-time (WebSocket) | < 50ms RTT |

---

## 5. Data Ownership & Cross-Cutting Concerns

| Concern | Implementation | Service Ownership |
|---------|---------------|-------------------|
| Authentication | OAuth2/OIDC via Auth Service | Auth Service (delegated) |
| Logging | Structured JSON via OpenTelemetry SDK | All services (standardized) |
| Metrics | Prometheus client library | All services (exporter pattern) |
| Tracing | OpenTelemetry TracerProvider | All services (propagated) |
| Config | Environment variables + ConfigMap | Platform-wide |
| Secrets | HashiCorp Vault / AWS Secrets Manager | Platform-wide |

---

## 6. Deployment Topology

### Development (Docker Compose)
- All services in single compose file
- Shared Redis/Postgres for simplicity

### Staging (Kubernetes)
- Namespaced per environment (`staging`, `prod`)
- Ingress controller for external traffic

### Production (Kubernetes)
- Multi-cluster with active-active failover
- Istio service mesh for mTLS + observability
- Prometheus Operator for metrics collection

---

## 7. Service Health & Resilience

| Service | Threshold | Timeout | Half-Open Window |
|---------|-----------|---------|------------------|
| Auth → Workspace | 5 failures/30s | 5s | 10s |
| Workspace → Sandbox | 3 failures/15s | 2s | 5s |
| Agentic → Ollama | 3 failures/10s | 5s | 10s |
| Observability → Prometheus | 3 failures/15s | 2s | 5s |

---

## 8. API Versioning Strategy
- **API version** in URL: `/api/v1/sandboxes`
- **Breaking changes**: New major version + deprecation header on old versions
- **Deprecation cycle**: 3 months notice before removal
