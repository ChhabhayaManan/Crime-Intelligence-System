# All AZs in the region; we use the first two.
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# --- AZ1 ---
resource "aws_subnet" "public_az1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "23.44.9.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-public-az1"
    Tier = "public"
  }
}

resource "aws_subnet" "private_az1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "23.44.10.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-private-az1"
    Tier = "app"
  }
}

resource "aws_subnet" "frontend_az1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "23.44.11.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-frontend-az1"
    Tier = "frontend"
  }
}

resource "aws_subnet" "data_az1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "23.44.12.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-data-az1"
    Tier = "data"
  }
}

# --- AZ2 ---
resource "aws_subnet" "public_az2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "23.44.19.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${var.project_name}-public-az2"
    Tier = "public"
  }
}

resource "aws_subnet" "private_az2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "23.44.20.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${var.project_name}-private-az2"
    Tier = "app"
  }
}

resource "aws_subnet" "frontend_az2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "23.44.21.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${var.project_name}-frontend-az2"
    Tier = "frontend"
  }
}

resource "aws_subnet" "data_az2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "23.44.22.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${var.project_name}-data-az2"
    Tier = "data"
  }
}

# ALB security group: public ingress on 80/443. Egress is restricted to the
# app port within the VPC so the ALB can only reach the ECS tasks (least
# privilege). Rules are inline here; do NOT attach standalone
# aws_security_group_rule resources to this SG (the AWS provider forbids
# mixing inline + standalone rules on one SG). Scoping egress to the VPC CIDR
# instead of the task SG keeps this self-contained (no vpc<->ecs cycle).
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "ALB ingress from internet on 80/443; egress to app port in-VPC"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP (redirected to HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "ALB to ECS tasks on the app port"
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# --- Route tables ---
# One shared public RT for both public subnets: default route to internet
# via the IGW.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_route_table_association" "public_az1" {
  subnet_id      = aws_subnet.public_az1.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_az2" {
  subnet_id      = aws_subnet.public_az2.id
  route_table_id = aws_route_table.public.id
}

# One shared private RT for both private subnets: no internet route (no NAT).
# Only the implicit local route + the S3 gateway-endpoint route, which the
# endpoints module attaches via route_table_ids.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

resource "aws_route_table_association" "private_az1" {
  subnet_id      = aws_subnet.private_az1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_az2" {
  subnet_id      = aws_subnet.private_az2.id
  route_table_id = aws_route_table.private.id
}

# Frontend + data tier subnets share the same private RT (no NAT, S3 gateway
# route only) — identical to the app (private) subnets above.
resource "aws_route_table_association" "frontend_az1" {
  subnet_id      = aws_subnet.frontend_az1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "frontend_az2" {
  subnet_id      = aws_subnet.frontend_az2.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "data_az1" {
  subnet_id      = aws_subnet.data_az1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "data_az2" {
  subnet_id      = aws_subnet.data_az2.id
  route_table_id = aws_route_table.private.id
}
