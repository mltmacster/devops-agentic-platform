# =============================================
# Terraform Module — EBS Volumes (AWS)
# =============================================

provider "aws" { region = var.region }

resource "aws_ebs_volume" "main" {
  count     = var.volume_count
  volume_size = var.volume_size_gb

  storage_type = var.storage_type
  encrypted    = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-ebs-${count + 1}"
  })
}

resource "aws_ebs_volume_attachment" "main" {
  count       = var.volume_count
  volume_id   = aws_ebs_volume.main[count].id
  instance_id = var.instance_ids[count % length(var.instance_ids)]

  device = "xvda${count + 1}"
}

output "volume_ids" { value = aws_ebs_volume.main[*].id }
