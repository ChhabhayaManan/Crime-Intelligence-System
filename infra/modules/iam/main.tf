data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  name                   = lower(var.project_name)
  account_id             = data.aws_caller_identity.current.account_id
  region                 = data.aws_region.current.name
  log_group_arn          = "arn:aws:logs:${local.region}:${local.account_id}:log-group:${var.log_group_name}:*"
  frontend_log_group_arn = "arn:aws:logs:${local.region}:${local.account_id}:log-group:${var.frontend_log_group_name}:*"

  # Built from the name so iam doesn't depend on the s3 module.
  evidence_bucket_arn = "arn:aws:s3:::${var.evidence_bucket_name}"

  # ECS ARNs the deploy role acts on. Built by string (names are deterministic
  # in the ecs module) to avoid an iam<->ecs dependency cycle.
  ecs_cluster_arn          = "arn:aws:ecs:${local.region}:${local.account_id}:cluster/${local.name}-cluster"
  ecs_service_arn          = "arn:aws:ecs:${local.region}:${local.account_id}:service/${local.name}-cluster/${local.name}-service"
  frontend_ecs_service_arn = "arn:aws:ecs:${local.region}:${local.account_id}:service/${local.name}-frontend-cluster/${local.name}-frontend-service"
  ecs_task_def_arn         = "arn:aws:ecs:${local.region}:${local.account_id}:task-definition/${local.name}-app:*"
  ecs_task_arn             = "arn:aws:ecs:${local.region}:${local.account_id}:task/${local.name}-cluster/*"

  # Terraform remote-state bucket (S3 backend). The terraform role needs full
  # access to read/write state and the use_lockfile lock object.
  tf_state_bucket_arn = "arn:aws:s3:::crime-is-terraform-state"
}

# GitHub Actions OIDC provider. Terraform-managed so OIDC setup is not a manual
# console step. The roles below federate against this provider.
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# Shared trust: ECS tasks assume both the task and execution roles.
data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# --- Role 1: task execution role (ECS control plane) ---
resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.project_name}-ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "execution" {
  # ECR auth token: AWS does not allow resource scoping on this action.
  statement {
    sid       = "EcrAuthToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # ECR image pull: scoped to the backend + frontend repos.
  statement {
    sid = "EcrPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
    ]
    resources = [var.ecr_repository_arn, var.frontend_ecr_repository_arn]
  }

  # CloudWatch Logs: scoped to the backend + frontend log groups.
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [local.log_group_arn, local.frontend_log_group_arn]
  }

  # Secrets injected at task start: scoped to exact secret ARNs.
  statement {
    sid       = "Secrets"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = var.secret_arns
  }
}

resource "aws_iam_role_policy" "execution" {
  name   = "execution"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.execution.json
}

# --- Role 2: task role (running FastAPI container) ---
resource "aws_iam_role" "ecs_task" {
  name               = "${var.project_name}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "task" {
  statement {
    sid       = "EvidenceObjectAccess"
    actions   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
    resources = ["${local.evidence_bucket_arn}/*"]
  }

  # HeadBucket (readiness check) + listing need bucket-level ListBucket.
  statement {
    sid       = "EvidenceBucketList"
    actions   = ["s3:ListBucket"]
    resources = [local.evidence_bucket_arn]
  }
}

resource "aws_iam_role_policy" "task" {
  name   = "task"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.task.json
}

# --- Role 3: github-actions deploy role (OIDC, no long-lived keys) ---
data "aws_iam_policy_document" "github_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # Only the main branch of this repo may assume the deploy role.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${var.project_name}-github-actions-deploy-role"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json
}

# Full deploy.yml scope: push image to ECR, run the one-off migration task,
# register a new task-def revision, and roll the service. Resource-scoped via
# string-built ECS ARNs (see locals) to keep least privilege without an
# iam<->ecs cycle.
data "aws_iam_policy_document" "github_actions" {
  statement {
    sid       = "EcrAuthToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "EcrPushPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
    ]
    resources = [var.ecr_repository_arn, var.frontend_ecr_repository_arn]
  }

  # Roll the backend + frontend services to new task-def revisions (deploy jobs).
  statement {
    sid       = "EcsDeploy"
    actions   = ["ecs:UpdateService", "ecs:DescribeServices"]
    resources = [local.ecs_service_arn, local.frontend_ecs_service_arn]
  }

  # Register/inspect task-def revisions. AWS does not support resource scoping
  # on these actions, so they must be "*".
  statement {
    sid       = "EcsRegisterTaskDef"
    actions   = ["ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition"]
    resources = ["*"]
  }

  # One-off DB migration: launch the task and wait on it.
  statement {
    sid       = "EcsRunMigration"
    actions   = ["ecs:RunTask"]
    resources = [local.ecs_task_def_arn]
  }

  statement {
    sid       = "EcsTrackMigration"
    actions   = ["ecs:DescribeTasks", "ecs:StopTask"]
    resources = [local.ecs_task_arn]
  }

  # Post-deploy health-check jobs verify health via the ELB API:
  #   - backend ALB is internal, so it cannot be HTTP-probed from a public
  #     runner. The backend check polls target-group health instead, which
  #     needs DescribeTargetGroups + DescribeTargetHealth.
  #   - the frontend ALB is internet-facing and still resolved by DNS to probe
  #     /_stcore/health, which needs DescribeLoadBalancers.
  # None of these actions support resource-level scoping, so a single "*"
  # statement covers them.
  statement {
    sid = "ElbDescribe"
    actions = [
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeTargetHealth",
    ]
    resources = ["*"]
  }

  # Hand the task + execution roles to ECS when registering/running tasks.
  statement {
    sid       = "PassEcsRoles"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.ecs_task_execution.arn, aws_iam_role.ecs_task.arn]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "github_actions" {
  name   = "deploy"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.github_actions.json
}

# --- Role 4: github-actions terraform role (OIDC, runs infra.yml) ---
# Trust allows the main branch (apply) AND pull requests (plan) of this repo.
data "aws_iam_policy_document" "github_terraform_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # main branch (apply) plus any pull request (plan-only) of this repo.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_repo}:ref:refs/heads/main",
        "repo:${var.github_repo}:pull_request",
      ]
    }
  }
}

resource "aws_iam_role" "github_actions_terraform" {
  name               = "${var.project_name}-github-actions-terraform-role"
  assume_role_policy = data.aws_iam_policy_document.github_terraform_assume.json
}

# Terraform must be able to create/modify/destroy the full stack on every run
# (plan reads everything; apply mutates everything). Scoping each action to a
# predicted resource ARN is infeasible for a tool that provisions the resources
# themselves, so this policy is intentionally broad across exactly the services
# the infra uses. The two narrow exceptions are pinned to specific resources:
#   - S3 state bucket: full access to read/write state + the use_lockfile lock.
#   - iam:PassRole is implicitly covered by the broad iam:* below (Terraform
#     attaches the ECS task/execution roles when registering task defs).
data "aws_iam_policy_document" "github_terraform" {
  statement {
    sid = "InfraServices"
    actions = [
      "ec2:*",                    # vpc, subnets, route tables, SGs, endpoints, EIP/NAT
      "elasticloadbalancing:*",   # alb module
      "rds:*",                    # rds module + read replica
      "ecs:*",                    # ecs cluster/service/task-def
      "ecr:*",                    # ecr repo
      "iam:*",                    # roles, policies, instance profiles, OIDC provider, PassRole
      "logs:*",                   # CloudWatch log groups
      "secretsmanager:*",         # db + jwt secrets
      "application-autoscaling:*" # ecs service autoscaling
    ]
    resources = ["*"]
  }

  # Terraform S3 backend: state object read/write + use_lockfile lock object.
  statement {
    sid       = "TerraformState"
    actions   = ["s3:*"]
    resources = [local.tf_state_bucket_arn, "${local.tf_state_bucket_arn}/*"]
  }

  # Evidence bucket and any other S3 the s3 module manages. Bucket-level S3
  # admin is needed to create/configure buckets; kept separate from the
  # state-bucket statement for clarity.
  statement {
    sid       = "S3Buckets"
    actions   = ["s3:*"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_actions_terraform" {
  name   = "terraform"
  role   = aws_iam_role.github_actions_terraform.id
  policy = data.aws_iam_policy_document.github_terraform.json
}
