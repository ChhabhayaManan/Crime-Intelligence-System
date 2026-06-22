variable "project_name" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

# Interface-endpoint ENIs land here (one per AZ).
variable "private_subnet_ids" {
  type = list(string)
}

# Route tables the S3 gateway endpoint attaches its prefix-list route to.
variable "private_route_table_ids" {
  type = list(string)
}

# Source of the 443 ingress; also the SG the egress rules are written onto.
variable "ecs_security_group_id" {
  type = string
}
