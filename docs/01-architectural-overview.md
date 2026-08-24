# DevOps Agentic Development Platform — Technical Architecture Document

## 1. Vision & Scope

**Platform Purpose:** A multi-tenant SaaS coding sandbox built on a custom Lite VM + Lite Linux Ubuntu OS, with an embedded Lite IDE and agentic AI coding assistants. Designed for developers (personal/professional) who need isolated, self-contained coding workspaces with enterprise-grade security and collaborative features.

**Core Principles:**
- **Open Source Based** — All core infrastructure is open-source (Apache 2.0 / MIT)
- **Agile & Modular** — Plugin-based architecture, hot-swappable components
- **Agnostic** — Language/runtimes agnostic (Python, Rust, JS/TS, Go, etc.)
- **Updatable** — Non-destructive updates via rolling deployments
- **Plug and Play** — One-click provisioning of new stacks (pgVector, pgML, Ollama, etc.)

---

## 2. System Overview — Mermaid Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[Browser / VS Code Extension]
        B[Mobile Dashboard App]
    end

    subgraph "Edge & Gateway"
        C[WAF + DDoS Protection]
        D[API Gateway (Kong / NGINX)]
        E[CDN (Static Assets / IDE Bundles)]
    end

    subgraph "Platform Control Plane"
        F[Auth Service (IAM/RBAC)]
        G[Workspace Orchestrator]
        H[Sandbox Lifecycle Manager]
        I[Agentic AI Engine]
        J[Observability Collector]
        K[Dashboard & Analytics]
    end

    subgraph "Platform Data Plane"
        L[Lite VM Pool (Ubuntu 24.04 Lite)]
        M1[Sandbox A: Python + FastAPI]
        M2[Sandbox B: Rust + Actix]
        M3[Sandbox C: Node.js + React]
    end

    subgraph "Shared Services"
        N[Redis (Session / Cache)]
        O[(PostgreSQL + pgVector 0.8.0)]
        P[MinIO / S3 (Artifacts)]
        Q[PostgresML + pgGraph]
    end

    A --> C --> D
    B --> D
    D --> F
    D --> G
    D --> H
    D --> I
    D --> K
    G --> J
    G --> L
    H --> L
    I --> L
    L --> M1
    L --> M2
    L --> M3
    M1 --> O
    M2 --> O
    M3 --> Q
    J --> K
