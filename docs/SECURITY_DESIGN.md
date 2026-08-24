# DevOps Agentic Development Platform — Security Design Document

## 1. Threat Model

### Trust Boundaries
```mermaid
graph TD
    subgraph "Untrusted World"
        A[Internet] --> B[WAF/DDoS Protection]
        B --> C[API Gateway]
    end
    
    subgraph "Trusted Zone"
        D[Auth Service (IAM/RBAC)]
        E[API Gateway] --> F[Sandbox Lifecycle Manager]
        G[Workspace Orchestrator]
        H[Agentic AI Engine]
    end
    
    subgraph "Sandbox Isolation"
        I[Lite VM Pool (Ubuntu 24.04 Lite)] --> J[Cilium eBPF Network Policy]
        K[User Namespace Mapping (root -> unprivileged)]
    end
    
    D --> E
    G --> E
    H --> E
    
    style A fill:#c0392b,stroke:#a93226
    style B fill:#e74c3c,stroke:#c0392b
    style C fill:#e67e22,stroke:#d35400
    style D fill:#f1c40f,stroke:#d4a017
    style E fill:#2ecc71,stroke:#27ae60
    style F fill:#3498db,stroke:#2980b9
    style G fill:#1abc9c,stroke:#16a085
    style H fill:#e74c3c,stroke:#c0392b
    style I fill:#8e44ad,stroke:#7d3c98
    style J fill:#2c3e50,stroke:#1a252f
    style K fill:#3498db,stroke:#2980b9
