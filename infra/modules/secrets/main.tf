# DATABASE_URL (full connection string) + JWT signing secret in Secrets
# Manager. Values come from the root module; never committed.
# recovery_window_in_days = 0 lets a destroyed secret name be reused
# immediately (avoids the 30-day soft-delete block on re-apply in dev).

resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${var.project_name}/database-url"
  description             = "Full DATABASE_URL (postgresql://...) for the app"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = var.database_url
}

resource "aws_secretsmanager_secret" "jwt" {
  name                    = "${var.project_name}/jwt-secret"
  description             = "JWT signing secret (HS256)"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id     = aws_secretsmanager_secret.jwt.id
  secret_string = var.jwt_secret
}
