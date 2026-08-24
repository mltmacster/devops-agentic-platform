# Observability & Dashboards — Metrics, Grafana, Monitoring

## 1. Architecture Overview

The observability layer collects, aggregates, and visualizes metrics from all platform components — sandboxes, agentic AI, IDE sessions, and infrastructure.

### Metrics Collection Pipeline
```mermaid
graph LR
    subgraph "Data Sources"
        A1[Sandbox Telemetry] --> B[Exporter: Prometheus Node Exporter]
        A2[Agentic AI Logs] --> C[Collector: Logstash/Fluentd]
        A3[Application Traces] --> D[Collector: Jaeger/OTLP]
        A4[IDE Telemetry] --> E[Exporter: Prometheus custom]
    end
    
    subgraph "Storage"
        B --> F[(Prometheus)]
        C --> G[(Loki / Elasticsearch)]
        D --> H[(Jaeger)]
        E --> F
    end
    
    subgraph "Visualization"
        F --> I[Grafana Dashboards]
        G --> J[Grafana (Logs)]
        H --> K[Jaeger UI]
    end
    
    I --> L[Admin Dashboard]
    J --> M[User Dashboard]
    K --> N[Diagnostics Panel]
