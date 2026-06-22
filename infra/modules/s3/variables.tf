variable "project_name" {
  type = string
}

variable "bucket_name" {
  description = "Globally-unique evidence bucket name"
  type        = string
}

# ECS task role ARN granted object access in the bucket policy.
variable "task_role_arn" {
  type = string
}
