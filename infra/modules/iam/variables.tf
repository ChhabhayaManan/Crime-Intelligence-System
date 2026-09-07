variable "project_name" {
  type = string
}

variable "ecr_repository_arn" {
  type = string
}

variable "frontend_ecr_repository_arn" {
  type = string
}

variable "k6_ecr_repository_arn" {
  type = string
}

variable "frontend_log_group_name" {
  type    = string
  default = "crime-is-frontend"
}

variable "secret_arns" {
  type = list(string)
}

variable "evidence_bucket_name" {
  type = string
}

variable "log_group_name" {
  type    = string
  default = "/ecs/crime-is"
}

variable "k6_log_group_name" {
  type    = string
  default = "/ecs/cis-k6"
}

variable "github_repo" {
  type    = string
  default = "ChhabhayaManan/Crime-Intelligence-System"
}
