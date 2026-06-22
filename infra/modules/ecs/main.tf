locals {
  name = lower(var.project_name)
}

resource "aws_ecs_cluster" "this" {
  name = "${local.name}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled" # cost control; flip to enabled for metrics
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# Container logs. Name must match the iam module's log_group_name so the
# execution role's scoped logs permission lines up.
resource "aws_cloudwatch_log_group" "app" {
  name              = var.log_group_name
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-logs"
  }
}

# --- ECS task security group ---
# Created with no inline rules; all rules are standalone so cross-module
# rules (ALB, RDS) can live here without conflict.
resource "aws_security_group" "task" {
  name        = "${var.project_name}-ecs-sg"
  description = "ECS Fargate tasks"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-ecs-sg"
  }
}

# App traffic: ALB -> task on the container port.
resource "aws_security_group_rule" "task_ingress_from_alb" {
  type                     = "ingress"
  from_port                = var.container_port
  to_port                  = var.container_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.task.id
  source_security_group_id = var.alb_security_group_id
  description              = "App port from ALB only"
}

# NOTE: ALB -> task egress lives inline on the ALB SG in the vpc module. The
# ALB SG uses inline rules, so a standalone egress rule here would conflict
# (the AWS provider forbids mixing inline + standalone rules on one SG).

# DB traffic: task -> RDS on the DB port.
resource "aws_security_group_rule" "task_egress_to_rds" {
  type                     = "egress"
  from_port                = var.db_port
  to_port                  = var.db_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.task.id
  source_security_group_id = var.rds_security_group_id
  description              = "Task to RDS"
}

resource "aws_security_group_rule" "rds_ingress_from_task" {
  type                     = "ingress"
  from_port                = var.db_port
  to_port                  = var.db_port
  protocol                 = "tcp"
  security_group_id        = var.rds_security_group_id
  source_security_group_id = aws_security_group.task.id
  description              = "RDS from ECS tasks only"
}

# NOTE: task egress :443 (to the interface-endpoint SG and the S3 prefix list)
# lives in the endpoints module, since both ends are created there.

# --- Task definition ---
resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name}-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = var.container_image
      essential = true

      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      # Plain (non-secret) RDS DNS. DATABASE_URL secret still wins in the app;
      # these expose writer/reader hosts for read-split wiring later.
      environment = [
        {
          name  = "DB_HOST"
          value = var.db_writer_host
        },
        {
          name  = "DB_HOST_READ"
          value = var.db_reader_host
        },
        {
          name  = "S3_EVIDENCE_BUCKET"
          value = var.evidence_bucket_name
        },
        {
          name  = "AWS_DEFAULT_REGION"
          value = var.region
        }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = var.database_url_secret_arn
        },
        {
          name      = "JWT_SECRET"
          valueFrom = var.jwt_secret_arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "app"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-app"
  }
}

# --- Service ---
# Fargate auto-balances tasks across the supplied private subnets (one per
# AZ), so desired_count = 2 lands one task in each AZ.
resource "aws_ecs_service" "app" {
  name            = "${local.name}-service"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "app"
    container_port   = var.container_port
  }

  # Give the container time to boot before the ALB starts failing it.
  health_check_grace_period_seconds = 60

  # CI (deploy.yml) registers new task-def revisions and rolls the service on
  # every app deploy. Terraform only knows the revision it created, so without
  # this it would revert the service to an older task def on the next apply.
  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = {
    Name = "${var.project_name}-service"
  }
}
