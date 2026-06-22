output "ecs_task_execution_role_arn" {
  value = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  value = aws_iam_role.ecs_task.arn
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "ecs_task_execution_role_name" {
  value = aws_iam_role.ecs_task_execution.name
}

output "ecs_task_role_name" {
  value = aws_iam_role.ecs_task.name
}

output "github_actions_role_name" {
  value = aws_iam_role.github_actions.name
}

output "github_oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.github.arn
}

output "github_actions_terraform_role_arn" {
  value = aws_iam_role.github_actions_terraform.arn
}

output "github_actions_terraform_role_name" {
  value = aws_iam_role.github_actions_terraform.name
}
