output "alb_arn" {
  value = aws_lb.this.arn
}

output "dns_name" {
  value = aws_lb.this.dns_name
}

output "zone_id" {
  value = aws_lb.this.zone_id
}

output "target_group_arn" {
  value = aws_lb_target_group.app.arn
}

output "backend_alb_sg_id" {
  value = aws_security_group.backend_alb.id
}

output "http_listener_arn" {
  value = aws_lb_listener.http.arn
}
