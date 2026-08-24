# =============================================
# Terraform — Staging Environment (DAP)
# =============================================

provider "terraform" { required_version = ">= 1.5.0" }
provider "aws" { region = "us-east-2" }

# ─── VPC Module ──────────────────────────────
module "vpc" {
  source = "${path.module}/modules/vpc"

  vpc_cidr     = "10.1.0.0/16"
  az_count     = 2
  project_name = "dap-staging"

  tags = { Environment = "staging"; Team = "platform" }
}

# ─── EKS Cluster ─────────────────────────────
module "eks" {
  source = "${path.module}/modules/eks"

  vpc_id              = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  project_name        = "dap-staging"

  tags = { Environment = "staging"; Team = "platform" }
}

# ─── EBS Volumes (staging shared storage) ──
module "ebs" {
  source = "${path.module}/modules/ebs"

  instance_ids    = module.ec2.instance_ids
  project_name    = "dap-staging"

  volume_size_gb = 200
  volume_count   = 5
}

# ─── EC2 Instances (staging node pool) ──────
module "ec2" {
  source = "${path.module}/modules/ec2"

  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids

  instance_count    = 2
  project_name      = "dap-staging"
}
