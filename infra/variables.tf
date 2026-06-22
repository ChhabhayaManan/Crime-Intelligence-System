variable "region" {
  default = "ap-south-1"
}

variable "project_name" {
  default = "Crime-IS"
}

variable "vpc_cidr" {
  default = "23.44.0.0/16"
}

# RDS master password. No default — set in gitignored terraform.tfvars.
variable "db_password" {
  type      = string
  sensitive = true
}

# Evidence S3 bucket name. Must be globally unique; suffix if taken.
# Shared by the s3 (creates it), iam (builds its ARN), and ecs (env var) modules.
variable "evidence_bucket_name" {
  type    = string
  default = "crime-is-evidence"
}

# Container image tag deployed by ECS (CI overrides with the git SHA).
variable "image_tag" {
  type    = string
  default = "latest"
}
