locals {
  name = lower(var.project_name)
}

# Target group: Fargate uses awsvpc networking, so targets are IPs.
# Health check is the shallow /health liveness probe (no DB).
resource "aws_lb_target_group" "app" {
  name                 = "${local.name}-tg"
  port                 = var.container_port
  protocol             = "HTTP"
  vpc_id               = var.vpc_id
  target_type          = "ip"
  deregistration_delay = 30

  health_check {
    path                = var.health_check_path
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
    timeout             = 5
    matcher             = "200"
  }

  tags = {
    Name = "${var.project_name}-tg"
  }
}

# Internal backend ALB security group. Standalone rules (not inline) so the
# frontend ECS SG can be referenced without creating a cross-SG cycle.
resource "aws_security_group" "backend_alb" {
  name        = "${var.project_name}-backend-alb-sg"
  description = "Internal backend ALB; reachable only from frontend ECS"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-backend-alb-sg"
  }
}

# NOTE: ingress on this SG from the frontend ECS SG is defined at the root
# (aws_security_group_rule.backend_alb_ingress_frontend in infra/main.tf) to
# avoid an alb<->frontend module dependency cycle.

resource "aws_security_group_rule" "backend_alb_egress_tasks" {
  type              = "egress"
  from_port         = var.container_port
  to_port           = var.container_port
  protocol          = "tcp"
  security_group_id = aws_security_group.backend_alb.id
  cidr_blocks       = [var.vpc_cidr]
  description       = "ALB to backend ECS tasks"
}

resource "aws_lb" "this" {
  name               = "${local.name}-alb"
  load_balancer_type = "application"
  internal           = true
  security_groups    = [aws_security_group.backend_alb.id]
  subnets            = var.subnet_ids

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# HTTP :80 -> forward to target group.
# TODO: once an ACM cert exists, change this action to a 301 redirect to
# HTTPS and add a :443 listener that forwards to the target group.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
