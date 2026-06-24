locals {
  name = lower(var.project_name)
}

# Internet-facing frontend ALB security group.
# Inline rules keep this SG self-contained, avoiding cross-SG cycles.
resource "aws_security_group" "frontend_alb" {
  name        = "${var.project_name}-frontend-alb-sg"
  description = "Internet-facing frontend ALB for Streamlit"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Listener is HTTP-only for now, but allow 443 ingress for future HTTPS.
  ingress {
    description = "HTTPS from anywhere (future)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "ALB to frontend ECS tasks"
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-frontend-alb-sg"
  }
}

# Target group: Fargate uses awsvpc networking, so targets are IPs.
# Health check is the Streamlit health endpoint.
resource "aws_lb_target_group" "app" {
  name                 = "${local.name}-frontend-tg"
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
    Name = "${var.project_name}-frontend-tg"
  }
}

resource "aws_lb" "this" {
  name               = "${local.name}-frontend-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.frontend_alb.id]
  subnets            = var.public_subnet_ids

  tags = {
    Name = "${var.project_name}-frontend-alb"
  }
}

# HTTP :80 -> forward to target group.
// TODO: add ACM cert + :443 listener + HTTP->HTTPS redirect if this ever goes public.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
