# DATABASE_URL (full connection string) + JWT signing secret live in Secrets
# Manager but are NOT managed by Terraform — the values were set once, out of
# band, and are read here as data sources so `apply` never rewrites them (no
# churn). ECS injects the live values at runtime via valueFrom = <arn>, so
# Terraform only needs the ARNs, never the secret values themselves.
#
# To rotate a value, edit the secret directly in Secrets Manager (console/CLI);
# Terraform is intentionally hands-off.

data "aws_secretsmanager_secret" "database_url" {
  name = "${var.project_name}/database-url"
}

data "aws_secretsmanager_secret" "jwt" {
  name = "${var.project_name}/jwt-secret"
}
