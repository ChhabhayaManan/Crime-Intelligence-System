variable "project_name" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

# App container port; the ALB SG egress is scoped to this port.
variable "container_port" {
  type    = number
  default = 8000
}
