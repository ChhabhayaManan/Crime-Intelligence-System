locals {
  name = lower(var.project_name)

  # Interface endpoints the ECS task needs at runtime (all HTTPS):
  #   ecr.api + ecr.dkr -> pull image manifest
  #   secretsmanager    -> execution role fetches DATABASE_URL + JWT_SECRET
  #   logs              -> awslogs driver ships container logs
  # (ECR layer *blobs* + the evidence bucket go over the S3 gateway below.)
  interface_services = toset([
    "ecr.api",
    "ecr.dkr",
    "secretsmanager",
    "logs",
  ])
}

# SG for the interface-endpoint ENIs: 443 from ECS tasks only. No egress block
# -> Terraform leaves egress empty (responses are stateful), so the endpoints
# can't initiate anything outbound.
resource "aws_security_group" "endpoints" {
  name        = "${var.project_name}-endpoints-sg"
  description = "VPC interface endpoints; 443 from ECS tasks only"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-endpoints-sg"
  }
}

resource "aws_security_group_rule" "endpoints_ingress_from_ecs" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.endpoints.id
  source_security_group_id = var.ecs_security_group_id
  description              = "HTTPS from ECS tasks"
}

# NOTE: ingress on the endpoints SG from the frontend ECS SG is defined at the
# root (aws_security_group_rule.endpoints_ingress_frontend in infra/main.tf) to
# avoid an endpoints<->frontend module dependency cycle.

# --- S3 gateway endpoint (free). Adds a prefix-list route to the private
# route table(s); reaches the evidence bucket + ECR layer blobs with no NAT. ---
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.private_route_table_ids

  tags = {
    Name = "${var.project_name}-s3-gw"
  }
}

# --- Interface endpoints: one ENI per private subnet (both AZs), 443, with
# private DNS so the AWS SDK resolves the normal service names to the ENIs. ---
resource "aws_vpc_endpoint" "interface" {
  for_each = local.interface_services

  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "${var.project_name}-${each.value}-endpoint"
  }
}

# --- ECS task egress :443. Defined here because both the endpoints SG and the
# S3 prefix list are created in this module. ---
resource "aws_security_group_rule" "ecs_egress_to_endpoints" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = var.ecs_security_group_id
  source_security_group_id = aws_security_group.endpoints.id
  description              = "ECS to interface endpoints (ECR/SecretsManager/logs)"
}

resource "aws_security_group_rule" "ecs_egress_to_s3" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = var.ecs_security_group_id
  prefix_list_ids   = [aws_vpc_endpoint.s3.prefix_list_id]
  description       = "ECS to S3 (evidence + ECR blobs) via gateway prefix list"
}
