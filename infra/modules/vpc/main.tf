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
