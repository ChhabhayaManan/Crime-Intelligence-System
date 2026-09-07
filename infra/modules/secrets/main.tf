data "aws_secretsmanager_secret" "database_url" {
  name = "${var.project_name}/database-url"
}

data "aws_secretsmanager_secret" "jwt" {
  name = "${var.project_name}/jwt-secret"
}
