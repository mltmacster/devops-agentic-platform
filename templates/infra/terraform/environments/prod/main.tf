# =============================================
# Terraform — Production Environment (DAP)
# =============================================

provider "terraform" { required_version = ">= 1.5.0" }
provider "aws" { region = "us-west-2" }

# ─── VPC Module (production — 3 AZs) ─────────
module "vpc" {
  source = "${path.module}/modules/vpc"

  vpc_cidr     = "10.2.0.0/16"
  az_count     = 3  # HA for production
  project_name = "dap-prod"

  tags = { Environment = "production"; Team = "platform" }
}

# ─── EKS Cluster (production-grade) ──────────
module "eks" {
  source = "${path.module}/modules/eks"

  vpc_id              = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  project_name        = "dap-prod"

  tags = { Environment = "production"; Team = "platform" }
}

# ─── EBS Volumes (prod — larger, more redundant) ──
module "ebs" {
  source = "${path.module}/modules/ebs"

  instance_ids    = module.ec2.instance_ids
  project_name    = "dap-prod"

  volume_size_gb = 500
  volume_count   = 12
}

# ─── EC2 Instances (prod node pool) ──────────
module "ec2" {
  source = "${path.module}/modules/ec2"

  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids

  instance_count    = 3  # HA for production
  project_name      = "dap-prod"
}
