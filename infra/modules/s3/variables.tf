variable "project_name" {
  type = string
}

variable "bucket_name" {
  description = "Globally-unique evidence bucket name"
  type        = string
}

variable "task_role_arn" {
  type = string
}

variable "force_destroy" {
  type    = bool
  default = false
}
