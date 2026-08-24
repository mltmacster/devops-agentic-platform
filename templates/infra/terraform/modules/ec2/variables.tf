# =============================================
# Terraform Module — EC2 Variables (AWS)
# =============================================

variable "region" { description = "AWS region"; type     = string; default = "us-east-1" }
variable "vpc_id" { description    = "VPC ID"; type       = string }
variable "public_subnet_ids" { description = "Public subnet IDs for internet access"; type = list(string) }
variable "private_subnet_ids" { description = "Private subnet IDs for instance placement"; type = list(string) }
variable "instance_type" { description   = "EC2 instance type"; type    = string; default = "t3.medium" }
variable "project_name" { description   = "Project name prefix"; type    = string; default = "dap" }
variable "node_group_name" { description = "Node group name for K8s"; type   = string; default = "dap-nodegroup" }
variable "user_data" { description  = "User data bash script for instances"; type   = list(string); default = ["# User data will be injected"] }
variable "instance_count" { description = "Number of instances to launch"; type = number; default = 1 }
variable "tags" { description = "Extra tags for resources"; type     = map(string); default = {} }
