# =============================================
# Terraform Module — VPC Variables (AWS)
# =============================================

variable "region" { description = "AWS region"; type      = string; default = "us-east-1" }
variable "vpc_cidr" { description = "VPC CIDR block"; type        = string; default = "10.0.0.0/16" }
variable "project_name" { description = "Project name prefix"; type     = string; default = "dap" }
variable "az_count" { description  = "Number of availability zones"; type = number; default = 2 }
variable "tags" { description = "Extra tags for resources"; type     = map(string); default = {} }
