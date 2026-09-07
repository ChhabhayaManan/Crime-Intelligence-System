locals {
  name = lower(var.project_name)
}

resource "aws_ecs_cluster" "this" {
  name = "${local.name}-k6-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Name = "${var.project_name}-k6-cluster"
  }
}

resource "aws_cloudwatch_log_group" "k6" {
  name              = var.log_group_name
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-k6-logs"
  }
}

resource "aws_security_group" "task" {
  name        = "${var.project_name}-k6-sg"
  description = "k6 load-test Fargate task (one-off, launched via run-task)"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-k6-sg"
  }
}

resource "aws_security_group_rule" "task_egress_to_backend_alb" {
  type                     = "egress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  security_group_id        = aws_security_group.task.id
  source_security_group_id = var.backend_alb_security_group_id
  description              = "To internal backend ALB (load test target)"
}

resource "aws_security_group_rule" "task_egress_to_endpoints" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.task.id
  source_security_group_id = var.endpoints_security_group_id
  description              = "To VPC interface endpoints ECR/logs"
}

resource "aws_security_group_rule" "task_egress_to_s3" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.task.id
  prefix_list_ids   = [var.s3_prefix_list_id]
  description       = "To S3 gateway for ECR image blobs"
}

resource "aws_ecs_task_definition" "k6" {
  family                   = "${local.name}-k6"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([
    {
      name      = "k6"
      image     = var.container_image
      essential = true

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.k6.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "k6"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-k6"
  }
}
