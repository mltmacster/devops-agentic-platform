# =============================================
# Terraform Module — EKS Cluster (AWS)
# =============================================

provider "aws" { region = var.region }

data "aws_availability_zones" "available" {}

resource "aws_eks_cluster" "main" {
  name     = "${var.project_name}-eks"
  role_arn = aws_iam_role.eks.arn

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.eks.id]
  }

  tags = merge(var.tags, { Name = "${var.project_name}-eks-cluster" })
}

resource "aws_iam_role" "eks" {
  name = "${var.project_name}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })

  tags = merge(var.tags, { Name = "${var.project_name}-eks-role" })
}

resource "aws_iam_role_policy_attachment" "eks_managed" {
  role       = aws_iam_role.eks.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_security_group" "eks" {
  name        = "${var.project_name}-eks-sg"
  description = "Security group for EKS cluster"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project_name}-eks-sg" })
}

output "cluster_endpoint" { value = aws_eks_cluster.main.endpoint }
output "cluster_name" { value = aws_eks_cluster.main.name }
