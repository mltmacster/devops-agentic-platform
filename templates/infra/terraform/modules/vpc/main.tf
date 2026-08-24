# =============================================
# Terraform Module — VPC (AWS)
# =============================================

# Create a VPC with public/private subnets across multiple AZs.

provider "aws" {
  region = var.region
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support    = true
  enable_dns_hostnames = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-vpc"
  })
}

resource "aws_vpc_cidr_block" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${var.project_name}-vpc-cidr-block"
  })
}

# Public subnets (for ALB, NAT Gateway)
resource "aws_subnet" "public" {
  count                   = var_az_count
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, "cidr_prefix", count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name                 = "${var.project_name}-public-${count.index + 1}"
    "kubernetes.io/role/elb" = "1"
    "kubernetes.io/cluster/${var.project_name}" = "public"
  })
}

# Private subnets (for workloads)
resource "aws_subnet" "private" {
  count = var_az_count

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, "cidr_prefix", count.index + var_az_count)
  availability_zone       = data.aws_availability_zones.available.names[count.index]

  tags = merge(var.tags, {
    Name                 = "${var.project_name}-private-${count.index + 1}"
    "kubernetes.io/role/internal-elb" = "1"
    "kubernetes.io/cluster/${var.project_name}" = "private"
  })
}

# Public NAT Gateway (one per AZ for HA)
resource "aws_nat_gateway" "public" {
  count         = var_az_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(var.tags, {
    Name = "${var.project_name}-nat-${count.index + 1}"
  })
}

resource "aws_eip" "nat" {
  count = var_az_count
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.project_name}-nat-eip-${count.index + 1}"
  })
}

# Internet Gateway for public subnets
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, { Name = "${var.project_name}-igw" })
}

# Route tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(var.tags, { Name = "${var.project_name}-public-rt" })
}

resource "aws_route_table_association" "public" {
  count          = var_az_count
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id

  tags = merge(var.tags, { Name = "${var.project_name}-public-rt-ass-${count.index}" })
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.public[0].id
  }

  tags = merge(var.tags, { Name = "${var.project_name}-private-rt" })
}

resource "aws_route_table_association" "private" {
  count          = var_az_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id

  tags = merge(var.tags, { Name = "${var.project_name}-private-rt-ass-${count.index}" })
}

# Output VPC + subnet IDs
output "vpc_id" { value = aws_vpc.main.id }
output "public_subnet_ids" { value = aws_subnet.public[*].id }
output "private_subnet_ids" { value = aws_subnet.private[*].id }
