output "repository_url" {
  description = "Full URI to push/pull (registry/repo)"
  value       = aws_ecr_repository.app.repository_url
}

output "repository_arn" {
  value = aws_ecr_repository.app.arn
}

output "repository_name" {
  value = aws_ecr_repository.app.name
}

output "registry_id" {
  description = "AWS account ID hosting the registry"
  value       = aws_ecr_repository.app.registry_id
}
