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
  container_image          = "${module.ecr.repository_url}:${var.image_tag}"
  frontend_container_image = "${module.ecr_frontend.repository_url}:${var.frontend_image_tag}"
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

module "ecr_frontend" {
  source       = "./modules/ecr"
  project_name = var.project_name
  repo_name    = "cis-frontend-image"
}

module "rds" {
  source              = "./modules/rds"
  project_name        = var.project_name
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.data_subnet_ids
  availability_zones  = module.vpc.availability_zones
  db_password         = var.db_password
  create_read_replica = true
}

module "secrets" {
  source       = "./modules/secrets"
  project_name = var.project_name
}

module "iam" {
  source                      = "./modules/iam"
  project_name                = var.project_name
  ecr_repository_arn          = module.ecr.repository_arn
  frontend_ecr_repository_arn = module.ecr_frontend.repository_arn
  secret_arns                 = [module.secrets.database_url_secret_arn, module.secrets.jwt_secret_arn]
  evidence_bucket_name        = var.evidence_bucket_name
}

module "s3" {
  source        = "./modules/s3"
  project_name  = var.project_name
  bucket_name   = var.evidence_bucket_name
  task_role_arn = module.iam.ecs_task_role_arn
}

# Backend ALB — now INTERNAL, in the app private subnets. Reachable only from
# the frontend ECS tasks (ingress rule hoisted to root below).
module "alb" {
  source       = "./modules/alb"
  project_name = var.project_name
  vpc_id       = module.vpc.vpc_id
  vpc_cidr     = var.vpc_cidr
  subnet_ids   = module.vpc.app_subnet_ids
}

# Frontend ALB — internet-facing, in the public subnets, fronts Streamlit.
module "frontend_alb" {
  source            = "./modules/frontend_alb"
  project_name      = var.project_name
  vpc_id            = module.vpc.vpc_id
  vpc_cidr          = var.vpc_cidr
  public_subnet_ids = module.vpc.public_subnet_ids
}

module "ecs" {
  source                  = "./modules/ecs"
  project_name            = var.project_name
  region                  = var.region
  vpc_id                  = module.vpc.vpc_id
  private_subnet_ids      = module.vpc.app_subnet_ids
  alb_security_group_id   = module.alb.backend_alb_sg_id
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

# Frontend ECS tier (Streamlit) behind the internet-facing frontend ALB. Calls
# the backend over the internal ALB via api_base_url (server-side, in-VPC).
module "frontend" {
  source                        = "./modules/frontend"
  project_name                  = var.project_name
  region                        = var.region
  vpc_id                        = module.vpc.vpc_id
  frontend_subnet_ids           = module.vpc.frontend_subnet_ids
  execution_role_arn            = module.iam.ecs_task_execution_role_arn
  container_image               = local.frontend_container_image
  api_base_url                  = "http://${module.alb.dns_name}/api/v1"
  frontend_alb_sg_id            = module.frontend_alb.frontend_alb_sg_id
  frontend_alb_target_group_arn = module.frontend_alb.target_group_arn
  backend_alb_sg_id             = module.alb.backend_alb_sg_id
  endpoints_security_group_id   = module.endpoints.endpoints_security_group_id
  s3_prefix_list_id             = module.endpoints.s3_prefix_list_id

  # Service create needs the frontend ALB listener attached first.
  depends_on = [module.frontend_alb]
}

# --- Cross-module SG rules hoisted to root to break module dependency cycles ---
# (alb/endpoints would otherwise depend on frontend, which depends on them.)

# Frontend ECS -> internal backend ALB (HTTP API on :80).
resource "aws_security_group_rule" "backend_alb_ingress_frontend" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  security_group_id        = module.alb.backend_alb_sg_id
  source_security_group_id = module.frontend.frontend_ecs_sg_id
  description              = "Internal backend ALB from frontend ECS only"
}

# Frontend ECS -> VPC interface endpoints (ECR pull + log shipping on :443).
resource "aws_security_group_rule" "endpoints_ingress_frontend" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = module.endpoints.endpoints_security_group_id
  source_security_group_id = module.frontend.frontend_ecs_sg_id
  description              = "HTTPS from frontend ECS tasks"
}
