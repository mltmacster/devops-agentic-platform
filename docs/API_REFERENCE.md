# DevOps Agentic Development Platform — API Reference

## Endpoints Overview

| Service | Base URL | Description |
|---------|----------|-------------|
| Auth Service | `http://localhost:8001` | OAuth2/OIDC auth, JWT tokens, RBAC checks |
| Workspace Orchestrator | `http://localhost:8002` | Tenant/workspace lifecycle management |
| Sandbox Lifecycle Manager | `http://localhost:8003` | VM boot/shutdown/suspend/resume operations |
| Agentic AI Engine | `http://localhost:8004` | Tool execution, agent orchestration, code completion |
| Observability Collector | `http://localhost:8005` | Metrics export, log aggregation |
| Dashboard API | `http://localhost:8006` | Admin panel, user panels (GraphQL) |

---

## Auth Service (`/auth`)

### POST /auth/login
**Authenticate and receive JWT token.**
```
Headers: Content-Type: application/json

Body:
{
  "email": "user@example.com",
  "password": "secret"
}

Response (200 OK):
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer"
}
```

### POST /auth/refresh
**Refresh an expired access token.**
```
Headers: Content-Type: application/json

Body:
{
  "refresh_token": "..."
}

Response (200 OK):
{
  "access_token": "...",
  "refresh_token": "..."
}
```

### GET /auth/me
**Get current user profile and roles.**
```
Headers: Authorization: Bearer <access_token>

Response (200 OK):
{
  "id": "user-123",
  "email": "dev@example.com",
  "role": "developer",
  "tenants": ["tenant-a"],
  "workspaces": ["ws-456"]
}
```

---

## Workspace Orchestrator (`/workspace`)

### POST /workspaces
**Create a new workspace.**
```
Headers: Authorization: Bearer <token>

Body:
{
  "name": "my-workspace",
  "tier": "pro"
}

Response (201 Created):
{
  "id": "ws-456",
  "name": "my-workspace",
  "tier": "pro",
  "status": "active"
}
```

### GET /workspaces/{id}
**Get workspace details.**
```
Headers: Authorization: Bearer <token>

Response (200 OK):
{
  "id": "ws-456",
  "name": "my-workspace",
  "tier": "pro",
  "status": "active",
  "sandboxes": [{"id": "sb-789"}],
  "quota": {
    "max_sandboxes": 3,
    "cpu_gb": 8.0,
    "memory_gb": 16.0,
    "disk_gb": 50.0
  }
}
```

### DELETE /workspaces/{id}
**Delete workspace (30-day grace period).**
```
Headers: Authorization: Bearer <token>

Response (204 No Content)
```

---

## Sandbox Lifecycle Manager (`/sandbox`)

### POST /sandboxes
**Create a new sandbox instance.**
```
Headers: Authorization: Bearer <token>

Body:
{
  "workspace_id": "ws-456",
  "stack": "python"
}

Response (201 Created):
{
  "id": "sb-789",
  "workspace_id": "ws-456",
  "stack": "python",
  "status": "creating"
}
```

### GET /sandboxes/{id}/status
**Get sandbox status.**
```
Headers: Authorization: Bearer <token>

Response (200 OK):
{
  "id": "sb-789",
  "status": "running",
  "stack": "python",
  "resources": {
    "cpu_cores_used": 0.3,
    "memory_mb_used": 256,
    "disk_gb_used": 4.5
  }
}
```

### POST /sandboxes/{id}/stop
**Gracefully stop a running sandbox.**
```
Headers: Authorization: Bearer <token>

Response (204 No Content)
```

### POST /sandboxes/{id}/suspend
**Checkpoint and pause a running sandbox.**
```
Headers: Authorization: Bearer <token>

Response (204 No Content)
```

### POST /sandboxes/{id}/resume
**Resume a suspended sandbox from checkpoint.**
```
Headers: Authorization: Bearer <token>

Response (204 No Content)
```

### DELETE /sandboxes/{id}
**Delete a stopped/suspended sandbox.**
```
Headers: Authorization: Bearer <token>

Response (204 No Content)
```

---

## Agentic AI Engine (`/agentic`)

### POST /agentic/run
**Execute an agentic AI workflow.**
```
Headers: Authorization: Bearer <token>

Body:
{
  "sandbox_id": "sb-789",
  "query": "Build a REST API for a todo app using FastAPI"
}

Response (200 OK):
{
  "request_id": "req-abc",
  "status": "completed",
  "agent_type": "Code Architect",
  "result": {
    "plan": ["Analyze requirements", "Generate scaffolding", "Create boilerplate"],
    "files_created": ["/workspace/app/main.py", "/workspace/app/models.py"]
  }
}
```

### WS /agentic/stream
**Streaming responses for long-running operations.**
```
Client → Server: {"request_id": "req-abc", "event_type": "progress"}
Server → Client: {"status": "running", "agent": "Code Architect", "step": 1}
Server → Client: {"status": "running", "agent": "Code Architect", "step": 2}
Server → Client: {"status": "completed", "result": {...}}
```

---

## Observability Collector (`/observability`)

### GET /metrics
**Export Prometheus metrics.**
```
Headers: Authorization: Bearer <token>

Response (200 OK, text/plain):
# HELP sandbox_total Total number of sandboxes
sandbox_total 5
# HELP ai_tokens_total Total tokens used by agentic AI
ai_tokens_total 125000
# HELP ai_latency_ms_avg Latency in milliseconds
ai_latency_ms_avg 245.6
```

---

## Dashboard API (`/dashboard`)

### GET /api/v1/dashboard/admin
**Admin panel overview.**
```
Headers: Authorization: Bearer <token>

Response (200 OK):
{
  "total_sandboxes": 5,
  "active_sandboxes": 3,
  "total_cpu_gb_allocated": 12.5,
  "total_memory_gb_allocated": 48.0,
  "active_users": 12,
  "ai_tokens_used_24h": 500000,
  "ai_avg_latency_ms": 245.6
}
```

### GET /api/v1/dashboard/user
**User panel overview.**
```
Headers: Authorization: Bearer <token>

Response (200 OK):
{
  "sandboxes": [
    {"id": "sb-789", "status": "running", "stack": "python"}
  ],
  "ai_history": [
    {"request_id": "req-abc", "status": "completed", "tokens_used": 150}
  ]
}
```
