variable "project_name" {
  type = string
}

# ECR repo ARN: image pull (execution) + push (github actions).
variable "ecr_repository_arn" {
  type = string
}

# Secret ARNs the execution role may read at task start (db + jwt).
variable "secret_arns" {
  type = list(string)
}

# Evidence bucket name; the ARN is built from it so iam does not depend on
# the s3 module (s3 depends on iam for the task-role ARN -> one-way).
variable "evidence_bucket_name" {
  type = string
}

# App CloudWatch log group name; must match the one the ecs module creates.
variable "log_group_name" {
  type    = string
  default = "/ecs/crime-is"
}

# GitHub repo allowed to assume the deploy role (owner/repo).
variable "github_repo" {
  type    = string
  default = "ChhabhayaManan/Crime-Intelligence-System"
}
