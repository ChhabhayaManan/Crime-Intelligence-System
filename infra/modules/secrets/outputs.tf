output "database_url_secret_arn" {
  value = data.aws_secretsmanager_secret.database_url.arn
}

output "jwt_secret_arn" {
  value = data.aws_secretsmanager_secret.jwt.arn
}
