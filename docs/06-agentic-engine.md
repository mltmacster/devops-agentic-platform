# Agentic AI Engine — Multi-Agent Architecture

## 1. Overview

The Agentic AI Engine is the brain of the platform, providing intelligent code assistance via a multi-agent system. It coordinates specialized agents for code generation, debugging, testing, research, and documentation — all running inside isolated sandbox environments.

### High-Level Architecture
```mermaid
graph TB
    A[Request: "Build REST API for a todo app"] --> B{Agentic Orchestrator}
    
    subgraph "Intent Analysis"
        C[Classifier: Code Architect Agent]
        D[Classifier: Debug Agent]
        E[Classifier: Test Generator]
    end
    
    B --> C & D & E
    
    subgraph "Agent Execution"
        F[Code Architect] -->|Plans scaffolding| G[Tool: Git init]
        G --> H[Tool: Create files]
        H --> I[Tool: Python run]
    end
    
    subgraph "Supporting Agents"
        J[Research Agent] -->|Finds docs| K[Crawle4AI: FastAPI docs]
        L[Test Agent] -->|Writes tests| M[Test Runner]
    end
    
    K --> F
    M --> N[Results Aggregator]
    
    subgraph "Tools (Plugin System)"
        O1[Git: commit, push, branch]
        O2[Crawle4AI: web scraping]
        O3[IBM Docling: PDF/text extraction]
        O4[LangGraph: multi-agent workflows]
        O5[Ollama: local LLM reasoning]
        O6[pgVector: semantic code search]
    end
    
    F --> O1 & O2
    L --> O6
    M --> O1
    
    N-->> A: Generated code + tests + run output
