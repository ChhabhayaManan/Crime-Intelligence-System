variable "project_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

# AZ names; [0] = primary (AZ-a), [1] = read replica (AZ-b).
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

# Days of automated backups. 1 = minimum that keeps backups on (free tier:
# backup storage up to the DB size is free). 0 would disable backups AND break
# the read replica (the source needs backups enabled).
variable "backup_retention_period" {
  type    = number
  default = 1
}

variable "create_read_replica" {
  type    = bool
  default = true
}
