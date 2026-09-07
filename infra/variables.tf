# variables that will be used in the main.tf file
variable "region" {
  default = "ap-south-1"
}

variable "project_name" {
  default = "Crime-IS"
}

variable "vpc_cidr" {
  default = "23.44.0.0/16"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "evidence_bucket_name" {
  type    = string
  default = "crime-is-evidence"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "frontend_image_tag" {
  type    = string
  default = "latest"
}

variable "k6_image_tag" {
  type    = string
  default = "latest"
}

variable "force_destroy" {
  type    = bool
  default = false
}
