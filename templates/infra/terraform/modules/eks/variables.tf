# =============================================
# Terraform Module — EKS Variables (AWS)
# =============================================

variable "region" { description = "AWS region"; type     = string; default = "us-east-1" }
variable "vpc_id" { description    = "VPC ID"; type       = string }
variable "private_subnet_ids" { description = "Private subnet IDs for EKS nodes"; type   = list(string) }
variable "project_name" { description = "Project name prefix"; type   = string; default = "dap" }
variable "node_group_name" { description = "Name for the node group"; type  = string; default = "dap-nodegroup" }
variable "tags" { description = "Extra tags for resources"; type     = map(string); default = {} }
