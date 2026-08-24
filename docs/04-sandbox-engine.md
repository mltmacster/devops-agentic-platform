# Sandbox Engine — Lite VM + Lite Linux Ubuntu OS

## 1. Architecture Overview

The sandbox engine manages isolated, self-contained development environments built on **Lite Ubuntu 24.04 LTS** running inside hardened containers (Podman/gVisor). Each sandbox is a complete Linux environment with full package management, network stack, and filesystem — but with strict isolation boundaries enforced by the host.

### Architecture Layers
```mermaid
graph TB
    subgraph "Host Layer (Trusted)"
        A[Ubuntu 24.04 Host OS]
    end

    subgraph "Orchestration Layer"
        B[Sandbox Lifecycle Manager (Python)]
        C[Podman / gVisor Runtime]
    end

    subgraph "Sandbox Instance (Isolated)"
        D[Lite Ubuntu 24.04 Container]
        E[User Namespace Mapping (root -> unprivileged)]
        F[eBPF Network Policy Enforcement]
    end

    subgraph "Development Stack (Inside Sandbox)"
        G[Python 3.12 + pip]
        H[Rust / cargo]
        I[Node.js 20 + npm/yarn]
        J[SQLite + pgVector + pgML]
        K[Ollama (local LLM)]
        L[Docker Compose (nested)]
    end

    A --> B
    B --> C
    C --> D & E & F
    D --> G & H & I & J & K & L

    style A fill:#2c3e50,stroke:#1a252f
    style B fill:#3498db,stroke:#2980b9
    style C fill:#2ecc71,stroke:#27ae60
    style D fill:#e74c3c,stroke:#c0392b
    style E fill:#f1c40f,stroke:#d4a017
    style F fill:#9b59b6,stroke:#8e44ad
