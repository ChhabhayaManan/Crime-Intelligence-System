output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "task_definition_family" {
  value = aws_ecs_task_definition.k6.family
}

output "task_definition_arn" {
  value = aws_ecs_task_definition.k6.arn
}

output "task_security_group_id" {
  value = aws_security_group.task.id
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.k6.name
}
