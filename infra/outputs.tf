output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnet_ids" {
  value = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "alb_security_group_id" {
  value = module.vpc.alb_security_group_id
}

output "ecr_repository_url" {
  value = module.ecr.repository_url
}

output "rds_writer_endpoint" {
  value = module.rds.writer_endpoint
}

output "rds_reader_endpoint" {
  value = module.rds.reader_endpoint
}

output "ecs_task_execution_role_arn" {
  value = module.iam.ecs_task_execution_role_arn
}

output "ecs_task_role_arn" {
  value = module.iam.ecs_task_role_arn
}

output "github_actions_role_arn" {
  value = module.iam.github_actions_role_arn
}

output "github_actions_terraform_role_arn" {
  value = module.iam.github_actions_terraform_role_arn
}

output "github_oidc_provider_arn" {
  value = module.iam.github_oidc_provider_arn
}

# Backend ALB is now INTERNAL — this DNS resolves only inside the VPC and is
# what the frontend tasks use as API_BASE_URL.
output "alb_dns_name" {
  value = module.alb.dns_name
}

# Internet-facing frontend ALB — the public entrypoint (browser hits this).
output "frontend_alb_dns_name" {
  value = module.frontend_alb.alb_dns_name
}

output "ecs_cluster_name" {
  value = module.ecs.cluster_name
}

output "ecs_service_name" {
  value = module.ecs.service_name
}

output "ecs_task_security_group_id" {
  value = module.ecs.task_security_group_id
}

output "endpoints_security_group_id" {
  value = module.endpoints.endpoints_security_group_id
}

output "s3_endpoint_id" {
  value = module.endpoints.s3_endpoint_id
}

output "evidence_bucket_arn" {
  value = module.s3.bucket_arn
}

output "evidence_bucket_name" {
  value = module.s3.bucket_name
}
