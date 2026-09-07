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

variable "execution_role_arn" {
  description = "Shared ECS execution role (ECR pull + logs) reused from the backend/frontend tasks"
  type        = string
}

variable "container_image" {
  description = "k6 image URI including tag (grafana/k6 base + test scripts)"
  type        = string
}

variable "backend_alb_security_group_id" {
  type = string
}

variable "endpoints_security_group_id" {
  type = string
}

variable "s3_prefix_list_id" {
  type = string
}

variable "cpu" {
  type    = number
  default = 1024
}

variable "memory" {
  type    = number
  default = 2048
}

variable "log_group_name" {
  type    = string
  default = "/ecs/cis-k6"
}

variable "log_retention_days" {
  type    = number
  default = 14
}
