# =============================================
# OpenAPI 3.0 Spec Template — DAP API
# =============================================

openapi: "3.0.3"
info:
  title: DevOps Agentic Development Platform API
  description: REST API for managing coding sandboxes, workspaces, and agentic AI features.
  version: "1.0.0"
  contact:
    name: DAP API Support
    email: api@devops-platform.example

servers:
  - url: http://localhost:8000/api/v1
    description: Development server

---
# =============================================
# Authentication Endpoints
# =============================================

post /auth/register:
  summary: Register a new developer account
  tags: [Auth]
  requestBody:
    content:
      application/json:
        schema:
          type: object
          properties:
            email: {type: string, format: email}
            password: {type: string, minLength: 12}
            team_id: {type: string, format: uuid}
  responses:
    '201':
      description: User created successfully
      content:
        application/json:
          schema:
            type: object
            properties:
              user_id: {type: string, format: uuid}
              access_token: {type: string}
              token_type: {type: string, constant: Bearer}
              expires_in: {type: integer}

post /auth/login:
  summary: Authenticate and receive JWT tokens
  tags: [Auth]
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required: [email, password]
          properties:
            email: {type: string}
            password: {type: string}
  responses:
    '200':
      description: Authentication successful
    '401':
      description: Invalid credentials

---
# =============================================
# Workspace Endpoints
# =============================================

get /workspaces:
  summary: List all workspaces for current user/tenant
  tags: [Workspaces]
  security: [{BearerAuth: []}]
  parameters:
    - in: query
      name: page
      schema: {type: integer, default: 1}
    - in: query
      name: limit
      schema: {type: integer, default: 20}
  responses:
    '200':
      description: Paginated workspace list
      content:
        application/json:
          schema:
            type: object
            properties:
              total: {type: integer}
              items: {type: array, items: {$ref: '#/components/schemas/Workspace'}}

post /workspaces:
  summary: Create a new development workspace
  tags: [Workspaces]
  security: [{BearerAuth: []}]
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required: [name, sandbox_type]
          properties:
            name: {type: string}
            sandbox_type: {type: string, enum: [podman, gvisor]}
            os_image: {type: string, default: ubuntu-24.04}
            resources:
              type: object
              properties:
                cpu: {type: number}
                memory: {type: string, format: byte}
  responses:
    '201':
      description: Workspace created successfully

delete /workspaces/{workspace_id}:
  summary: Delete a workspace and its sandbox
  tags: [Workspaces]
  security: [{BearerAuth: []}]
  parameters:
    - name: workspace_id
      in: path
      required: true
      schema: {type: string, format: uuid}
  responses:
    '204':
      description: Workspace deleted successfully

---
# =============================================
# Agentic AI Engine Endpoints
# =============================================

post /ai/execute:
  summary: Execute a task with agentic AI
  tags: [AI Engine]
  security: [{BearerAuth: []}]
  requestBody:
    content:
      application/json:
        schema:
          type: object
          required: [task_type, workspace_id]
          properties:
            task_type: {type: string, enum: [code_gen, debug, test_gen, research]}
            workspace_id: {type: string, format: uuid}
            prompt: {type: string}
            model: {type: string, default: code-llama-7b}
  responses:
    '200':
      description: Task execution started (streaming response)

---
# =============================================
# IDE Endpoints
# =============================================

get /ide/config:
  summary: Get Monaco Editor configuration for current workspace
  tags: [IDE]
  security: [{BearerAuth: []}]
  parameters:
    - name: workspace_id
      in: path
      required: true
      schema: {type: string, format: uuid}
  responses:
    '200':
      description: Editor configuration

ws /ide/ws/{workspace_id}:
  summary: WebSocket connection for IDE live sync
  tags: [IDE]
  security: [{BearerAuth: []}]

---
# =============================================
# Observability Endpoints
# =============================================

get /metrics:
  summary: Prometheus metrics endpoint
  tags: [Observability]
  security: [{BearerAuth: []}]
  responses:
    '200':
      description: Prometheus metrics (text/plain)

get /healthz:
  summary: Service health check
  tags: [Observability]
  responses:
    '200':
      description: Service healthy
    '5xx':
      description: Service unhealthy
