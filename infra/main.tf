terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  # Full app connection string; writer endpoint + custom port from RDS.
  database_url    = "postgresql://${module.rds.db_username}:${var.db_password}@${module.rds.writer_address}:${module.rds.port}/${module.rds.db_name}"
  container_image = "${module.ecr.repository_url}:${var.image_tag}"
}

module "vpc" {
  source       = "./modules/vpc"
  project_name = var.project_name
  vpc_cidr     = var.vpc_cidr
}

module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
}

module "rds" {
  source              = "./modules/rds"
  project_name        = var.project_name
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  availability_zones  = module.vpc.availability_zones
  db_password         = var.db_password
  create_read_replica = true
}

module "secrets" {
  source       = "./modules/secrets"
  project_name = var.project_name
  database_url = local.database_url
  jwt_secret   = var.jwt_secret
}

module "iam" {
  source               = "./modules/iam"
  project_name         = var.project_name
  ecr_repository_arn   = module.ecr.repository_arn
  secret_arns          = [module.secrets.database_url_secret_arn, module.secrets.jwt_secret_arn]
  evidence_bucket_name = var.evidence_bucket_name
}

module "s3" {
  source        = "./modules/s3"
  project_name  = var.project_name
  bucket_name   = var.evidence_bucket_name
  task_role_arn = module.iam.ecs_task_role_arn
}

module "alb" {
  source                = "./modules/alb"
  project_name          = var.project_name
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  alb_security_group_id = module.vpc.alb_security_group_id
}

module "ecs" {
  source                  = "./modules/ecs"
  project_name            = var.project_name
  region                  = var.region
  vpc_id                  = module.vpc.vpc_id
  private_subnet_ids      = module.vpc.private_subnet_ids
  alb_security_group_id   = module.vpc.alb_security_group_id
  rds_security_group_id   = module.rds.security_group_id
  execution_role_arn      = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn
  container_image         = local.container_image
  database_url_secret_arn = module.secrets.database_url_secret_arn
  jwt_secret_arn          = module.secrets.jwt_secret_arn
  target_group_arn        = module.alb.target_group_arn
  db_writer_host          = module.rds.writer_address
  db_reader_host          = coalesce(module.rds.reader_address, module.rds.writer_address)
  evidence_bucket_name    = var.evidence_bucket_name

  # Service create needs the listener attached to the LB first.
  depends_on = [module.alb]
}

module "endpoints" {
  source                  = "./modules/endpoints"
  project_name            = var.project_name
  region                  = var.region
  vpc_id                  = module.vpc.vpc_id
  private_subnet_ids      = module.vpc.private_subnet_ids
  private_route_table_ids = module.vpc.private_route_table_ids
  ecs_security_group_id   = module.ecs.task_security_group_id
}
