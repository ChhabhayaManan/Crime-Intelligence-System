locals {
  name = lower(var.project_name)
}

resource "aws_ecs_cluster" "this" {
  name = "${local.name}-frontend-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Name = "${var.project_name}-frontend-cluster"
  }
}

resource "aws_cloudwatch_log_group" "app" {
  name              = var.log_group_name
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-frontend-logs"
  }
}

resource "aws_security_group" "task" {
  name        = "${var.project_name}-frontend-ecs-sg"
  description = "Frontend ECS Fargate tasks (Streamlit)"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-frontend-ecs-sg"
  }
}

resource "aws_security_group_rule" "task_ingress_from_alb" {
  type                     = "ingress"
  from_port                = var.container_port
  to_port                  = var.container_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.task.id
  source_security_group_id = var.frontend_alb_sg_id
  description              = "Streamlit port from frontend ALB"
}

resource "aws_security_group_rule" "task_egress_to_backend_alb" {
  type                     = "egress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  security_group_id        = aws_security_group.task.id
  source_security_group_id = var.backend_alb_sg_id
  description              = "To internal backend ALB / API"
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

resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name}-frontend-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = var.container_image
      essential = true

      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "API_BASE_URL"
          value = var.api_base_url
        },
        {
          name  = "AWS_DEFAULT_REGION"
          value = var.region
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "frontend"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-frontend-app"
  }
}

resource "aws_ecs_service" "app" {
  name            = "${local.name}-frontend-service"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.frontend_subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.frontend_alb_target_group_arn
    container_name   = "frontend"
    container_port   = var.container_port
  }

  health_check_grace_period_seconds = 60

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = {
    Name = "${var.project_name}-frontend-service"
  }
}
