variable "project_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "availability_zones" {
  type = list(string)
}

variable "db_name" {
  type    = string
  default = "crimedb"
}

variable "port" {
  type    = number
  default = 3456
}

variable "db_username" {
  type    = string
  default = "crimeadmin"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "allocated_storage" {
  type    = number
  default = 20
}

variable "engine_version" {
  type    = string
  default = "16"
}

variable "backup_retention_period" {
  type    = number
  default = 1
}

variable "create_read_replica" {
  type    = bool
  default = true
}
