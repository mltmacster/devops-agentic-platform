# =============================================
# Infrastructure Templates (DAP)
# =============================================

Pre-built, reusable infrastructure templates for the DevOps Agentic Platform.

## Structure

```
templates/infra/
├── helm/                  # Helm charts for K8s deployments
│   └── chart-template/    # Reusable HCL template for all 6 services
├── terraform/             # AWS infrastructure via Terraform
│   ├── environments/      # Environment-specific configs (dev/staging/prod)
│   │   ├── dev/main.tf    # Development environment
│   │   ├── staging/main.tf# Staging environment  
│   │   └── prod/main.tf   # Production environment (3 AZs, HA)
│   └── modules/           # Reusable Terraform modules
│       ├── vpc/           # VPC with public/private subnets, IGW, NAT
│       ├── eks/           # EKS cluster + IAM role
│       ├── ec2/           # EC2 instances for node pools
│       └── ebs/           # EBS volumes for shared storage
├── kubernetes/            # Raw K8s manifests (non-Helm)
│   ├── K8S_DEPLOYMENT.yml # Deployment, Service, NetworkPolicy
└── docker/                # Docker Compose & Dockerfile templates
```

## Quick Start (Terraform)

```bash
# Create workspace for dev environment
cd templates/terraform/environments/dev
terraform init
terraform plan
terraform apply -auto-approve

# For staging/prod: use the respective environment directory
```

## Quick Start (Helm)

```bash
# Clone template and customize per-service values
cp chart-template/ services/<service-name>/

# Deploy to a K8s cluster
helm install <release> ./services/<service-name>/ \
  --namespace dap \
  -f services/<service-name>/values-<service-name>.yaml
```

## Services Covered

| Service | Helm Chart | Terraform Module | Purpose |
|---------|-----------|------------------|---------|
| api-gateway | `chart-template/` | — | API routing & auth |
| auth-service | `chart-template/` | — | OAuth2/RBAC management |
| workspace-svc | `chart-template/` | — | Multi-tenant orchestration |
| sandbox-engine | `chart-template/` | — | VM lifecycle management |
| ide-core | `chart-template/` | — | Embedded IDE API |
| observability | `chart-template/` | — | Metrics collection & dashboards |
