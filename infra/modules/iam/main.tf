data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  name                   = lower(var.project_name)
  account_id             = data.aws_caller_identity.current.account_id
  region                 = data.aws_region.current.name
  log_group_arn          = "arn:aws:logs:${local.region}:${local.account_id}:log-group:${var.log_group_name}:*"
  frontend_log_group_arn = "arn:aws:logs:${local.region}:${local.account_id}:log-group:${var.frontend_log_group_name}:*"
  k6_log_group_arn       = "arn:aws:logs:${local.region}:${local.account_id}:log-group:${var.k6_log_group_name}:*"

  evidence_bucket_arn = "arn:aws:s3:::${var.evidence_bucket_name}"

  ecs_cluster_arn          = "arn:aws:ecs:${local.region}:${local.account_id}:cluster/${local.name}-cluster"
  ecs_service_arn          = "arn:aws:ecs:${local.region}:${local.account_id}:service/${local.name}-cluster/${local.name}-service"
  frontend_ecs_service_arn = "arn:aws:ecs:${local.region}:${local.account_id}:service/${local.name}-frontend-cluster/${local.name}-frontend-service"
  ecs_task_def_arn         = "arn:aws:ecs:${local.region}:${local.account_id}:task-definition/${local.name}-app:*"
  ecs_task_arn             = "arn:aws:ecs:${local.region}:${local.account_id}:task/${local.name}-cluster/*"

  tf_state_bucket_arn = "arn:aws:s3:::crime-is-terraform-state"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.project_name}-ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid       = "EcrAuthToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "EcrPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
    ]
    resources = [var.ecr_repository_arn, var.frontend_ecr_repository_arn, var.k6_ecr_repository_arn]
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [local.log_group_arn, local.frontend_log_group_arn, local.k6_log_group_arn]
  }

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
    resources = [var.ecr_repository_arn, var.frontend_ecr_repository_arn, var.k6_ecr_repository_arn]
  }

  statement {
    sid       = "EcsDeploy"
    actions   = ["ecs:UpdateService", "ecs:DescribeServices"]
    resources = [local.ecs_service_arn, local.frontend_ecs_service_arn]
  }

  statement {
    sid       = "EcsRegisterTaskDef"
    actions   = ["ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition"]
    resources = ["*"]
  }

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

  statement {
    sid = "ElbDescribe"
    actions = [
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeTargetHealth",
    ]
    resources = ["*"]
  }

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

data "aws_iam_policy_document" "github_terraform" {
  statement {
    sid = "InfraServices"
    actions = [
      "ec2:*",
      "elasticloadbalancing:*",
      "rds:*",
      "ecs:*",
      "ecr:*",
      "iam:*",
      "logs:*",
      "secretsmanager:*",
      "application-autoscaling:*"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "TerraformState"
    actions   = ["s3:*"]
    resources = [local.tf_state_bucket_arn, "${local.tf_state_bucket_arn}/*"]
  }

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
