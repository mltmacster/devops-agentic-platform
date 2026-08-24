# Embedded IDE — Monaco Editor / VS Code Web Integration

## 1. Architecture Overview

The embedded IDE is built on **Monaco Editor** (VS Code's editor core) running in a WebAssembly/WebGL container, connected to the sandbox via WebSocket. It provides full IDE experience — syntax highlighting, LSP diagnostics, integrated terminal — without the overhead of a full VS Code shell.

### Architecture Layers
```mermaid
graph TB
    subgraph "Client Layer"
        A[Browser / VS Code Extension]
        B[Monaco Editor DOM]
    end
    
    subgraph "WebSocket Bridge"
        C[Node.js WebSocket Server]
        D[LSP Proxy]
    end
    
    subgraph "Sandbox (gVisor / Podman)"
        E[Language Server Protocol Servers]
        F[Node.js LSP Provider]
        G[Python LSP (pygls)]
        H[Rust Analyzer]
    end
    
    subgraph "Shared Services"
        J[(PostgreSQL + pgVector)]  # Code search / RAG context
    end
    
    A --> B
    B --> C
    C --> D
    D --> E & F & G & H
    
    style A fill:#3498db,stroke:#2980b9
    style B fill:#2ecc71,stroke:#27ae60
    style C fill:#f39c12,stroke:#b7791a
    style D fill:#e67e22,stroke:#d35400
