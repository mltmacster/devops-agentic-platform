# =============================================
# Terraform Module — EC2 Instances (AWS)
# =============================================

provider "aws" { region = var.region }

resource "aws_instance" "main" {
  count                 = var.instance_count
  ami                   = data.aws_ami.ubuntu.id
  instance_type         = var.instance_type

  vpc_subnet_id        = var.public_subnet_ids[count % length(var.public_subnet_ids)]
  subnet_ids          = [var.private_subnet_ids[count % length(var.private_subnet_ids)]]

  ami_launch_options {
    user_data = base64encode(var.user_data | join("\n", []))
  }

  tags = merge(var.tags, {
    Name                    = "${var.project_name}-instance-${count + 1}"
    "kubernetes.io/cluster/${var.project_name}" = var.node_group_name
  })
}

output "instance_ids" { value = aws_instance.main[*].id }
output "private_ips" { value = aws_instance.main[*].private_ip_address }
