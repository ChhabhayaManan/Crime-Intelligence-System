variable "project_name" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "frontend_subnet_ids" {
  description = "Frontend tier private subnets (one per AZ)"
  type        = list(string)
}

variable "execution_role_arn" {
  description = "Reuses the backend ECS task execution role (ECR pull + logs)"
  type        = string
}

variable "task_role_arn" {
  description = "Frontend needs no AWS APIs; leave null for no task role"
  type        = string
  default     = null
}

variable "container_image" {
  description = "Frontend ECR image URI including tag"
  type        = string
}

variable "container_port" {
  type    = number
  default = 8501
}

variable "api_base_url" {
  description = "Full backend internal ALB URL incl. /api/v1; injected as API_BASE_URL env"
  type        = string
}

variable "frontend_alb_sg_id" {
  description = "Frontend ALB security group (source for ingress on container_port)"
  type        = string
}

variable "frontend_alb_target_group_arn" {
  type = string
}

variable "backend_alb_sg_id" {
  description = "Internal backend ALB security group (egress target on 80)"
  type        = string
}

variable "endpoints_security_group_id" {
  description = "VPC interface-endpoints SG (egress 443 for ECR/logs)"
  type        = string
}

variable "s3_prefix_list_id" {
  description = "S3 gateway prefix list id (egress 443 for ECR image blobs)"
  type        = string
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

variable "log_group_name" {
  type    = string
  default = "crime-is-frontend"
}

variable "log_retention_days" {
  type    = number
  default = 30
}
