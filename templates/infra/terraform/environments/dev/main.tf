# =============================================
# Terraform — Development Environment (DAP)
# =============================================

provider "terraform" { required_version = ">= 1.5.0" }

# ─── VPC Module ──────────────────────────────
module "vpc" {
  source = "${path.module}/modules/vpc"

  vpc_cidr     = "10.0.0.0/16"
  az_count     = 2
  project_name = "dap-dev"

  tags = {
    Environment = "dev"
    Team        = "platform"
  }
}

# ─── EKS Cluster ─────────────────────────────
module "eks" {
  source = "${path.module}/modules/eks"

  vpc_id              = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  project_name        = "dap-dev"

  tags = { Environment = "dev"; Team = "platform" }
}

# ─── EBS Volumes (for dev shared storage) ──
module "ebs" {
  source = "${path.module}/modules/ebs"

  instance_ids    = module.ec2.instance_ids
  project_name    = "dap-dev"

  volume_size_gb = 100
  volume_count   = 3
}

# ─── EC2 Instances (dev node pool) ──────────
module "ec2" {
  source = "${path.module}/modules/ec2"

  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids

  instance_count    = 1
  project_name      = "dap-dev"
}
