variable "project_name" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "alb_security_group_id" {
  type = string
}

variable "rds_security_group_id" {
  type = string
}

variable "execution_role_arn" {
  type = string
}

variable "task_role_arn" {
  type = string
}

variable "container_image" {
  description = "ECR image URI including tag"
  type        = string
}

variable "app_env" {
  description = "ENV env var passed to the container"
  type        = string
  default     = "production"
}

variable "db_writer_host" {
  description = "RDS primary hostname (writes)"
  type        = string
}

variable "db_reader_host" {
  description = "RDS read replica hostname (reads)"
  type        = string
}

variable "evidence_bucket_name" {
  description = "S3 evidence bucket name (S3_EVIDENCE_BUCKET env)"
  type        = string
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "db_port" {
  type    = number
  default = 3456
}

variable "desired_count" {
  type    = number
  default = 2
}

# Smallest valid Fargate combo (0.25 vCPU / 0.5 GB).
variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "database_url_secret_arn" {
  type = string
}

variable "jwt_secret_arn" {
  type = string
}

variable "target_group_arn" {
  type = string
}

variable "log_group_name" {
  type    = string
  default = "/ecs/crime-is"
}

variable "log_retention_days" {
  type    = number
  default = 14
}
