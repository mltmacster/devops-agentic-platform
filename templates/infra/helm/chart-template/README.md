# =============================================
# Helm Chart — DAP Microservice Template (README)
# =============================================

## Usage

This is a reusable Helm chart template for all 6 microservices in the
DevOps Agentic Platform: gateway, auth, workspace, sandbox, ide, observability.

### Quick Start

```bash
# Clone the template and customize
git clone https://github.com/dap/chart-template.git
cd chart-template

# Copy and customize values
cp values.yaml values-<service-name>.yaml

# Deploy with Helm
helm install <release-name> ./ \
  --values values-<service-name>.yaml \
  --namespace dap
```

### Required Values

| Value | Default | Description |
|-------|---------|-------------|
| `replicaCount` | 2 | Number of pod replicas |
| `image.repository` | ghcr.io/dap/<name> | Container image registry |
| `containerPorts.http` | 8000 | HTTP port exposed by the pod |

### Optional Values

| Value | Default | Description |
|-------|---------|-------------|
| `strategy.type` | RollingUpdate | Deployment strategy |
| `ingress.enabled` | false | Enable ingress controller |
| `resources.limits.cpu` | 100m | CPU limit per pod |

### Directory Structure

```
chart-template/
├── Chart.yaml          # Chart metadata
├── values.yaml         # Default values (override with --values)
├── templates/          # K8s manifests (Deployment, Service, etc.)
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
└── README.md           # This file
```

### K8s Manifest Templates

All manifests follow Kubernetes best practices:
- **NetworkPolicy** — zero-trust ingress/egress rules
- **PodSecurityContext** — non-root user, read-only filesystem where possible
- **Probes** — liveness and readiness with configurable intervals
- **Resource Limits** — CPU/memory to prevent noisy neighbors
