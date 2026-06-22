# CI/CD Pipeline — Bootstrap & Operations

This directory holds the GitHub Actions workflows for Crime-IS (project `Crime-IS`,
region `ap-south-1`).

| Workflow | Trigger | OIDC role | Purpose |
|---|---|---|---|
| `infra.yml` | push to `main` (`infra/**`), PR (`infra/**`), manual | `Crime-IS-github-actions-terraform-role` | `terraform fmt/validate/plan` on PRs, `apply` on `main` |
| `deploy.yml` | push to `main`, manual | `Crime-IS-github-actions-deploy-role` | build+push image, run DB migration task, roll the ECS service |

Both use GitHub OIDC (no long-lived AWS keys). The OIDC provider and both roles are
Terraform-managed in `infra/modules/iam`.

## One-time bootstrap (manual, in order)

These steps create the things Terraform/CI cannot create for themselves.

1. **Create the Terraform state bucket** (Terraform cannot create its own backend):
   ```bash
   aws s3api create-bucket \
     --bucket crime-is-terraform-state \
     --region ap-south-1 \
     --create-bucket-configuration LocationConstraint=ap-south-1
   aws s3api put-bucket-versioning \
     --bucket crime-is-terraform-state \
     --versioning-configuration Status=Enabled
   ```
   The S3 backend uses `use_lockfile = true` (no DynamoDB lock table).

2. **First `terraform apply` locally** — stands up the OIDC provider, all four IAM
   roles, and the full stack. CI cannot assume any role until this exists.
   ```bash
   cd infra
   terraform init
   # db_password / jwt_secret are sensitive with no default — supply via
   # gitignored terraform.tfvars or TF_VAR_db_password / TF_VAR_jwt_secret env vars.
   export TF_VAR_db_password='...'
   export TF_VAR_jwt_secret='...'
   terraform apply
   ```
   Note the outputs `github_actions_terraform_role_arn`, `github_actions_role_arn`
   (deploy), and `github_oidc_provider_arn`.

3. **Push the first image by hand** (proves build/push/run before CI relies on it):
   ```bash
   ACCOUNT_ID=<your account id>
   aws ecr get-login-password --region ap-south-1 \
     | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com"
   docker build -t "$ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/cis-image:latest" .
   docker push "$ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/cis-image:latest"
   ```

After this, pushing to `main` runs `deploy.yml` end to end, and `infra/**` changes
flow through `infra.yml`.

## Required GitHub configuration

Set these under **Settings → Secrets and variables → Actions**.

### Repository **secrets**
| Secret | Used by | Notes |
|---|---|---|
| `TF_VAR_db_password` | `infra.yml` | RDS master password; sensitive, no default |
| `TF_VAR_jwt_secret`  | `infra.yml` | App JWT signing secret; sensitive, no default |

### Repository **variables**
| Variable | Used by | Example / notes |
|---|---|---|
| `AWS_ACCOUNT_ID` | both | 12-digit account id; used to build the role ARNs |
| `AWS_REGION` | both | `ap-south-1` |
| `PRIVATE_SUBNET_IDS` | `deploy.yml` (optional) | Comma-separated private subnet IDs for the migration task. **Optional** — if unset, the workflow resolves them from the `Tier=private` subnet tag. |
| `ECS_TASK_SG_ID` | `deploy.yml` (optional) | ECS task security group id. **Optional** — if unset, resolved from the `Crime-IS-ecs-sg` Name tag. |

The role ARNs are not configured directly; they are built in-workflow as
`arn:aws:iam::${AWS_ACCOUNT_ID}:role/Crime-IS-github-actions-terraform-role` and
`...-deploy-role`. The role names are fixed by the iam module
(`${project_name}-github-actions-{terraform,deploy}-role`).

## How `deploy.yml` works

1. **build-push** — builds the image, tags it `git-<SHA>` and `latest`, pushes both to
   ECR repo `cis-image`. The `git-<SHA>` tag is the output threaded to later jobs.
2. **migrate** — resolves the private subnets + ECS task SG, then `aws ecs run-task`
   (FARGATE) against the `crime-is-app` task-def with command override
   `python -m App.db.setup_db`, waits for `tasks-stopped`, and fails unless the `app`
   container exit code is `0`.
3. **deploy** — re-renders the `crime-is-app` task-def with the new `git-<SHA>` image
   (via `describe-task-definition` + `jq`), registers a new revision, updates
   `crime-is-service`, and waits for the service to stabilize.

`infra.yml` runs `plan` on PRs (commented back, job fails on plan error) and
`apply -auto-approve` only on push to `main`.

## Notes

- All actions are pinned to major versions: `@v4` (checkout, configure-aws-credentials,
  setup-terraform inputs), `@v3` (setup-terraform), `@v2` (amazon-ecr-login,
  amazon-ecs-deploy-task-definition), `@v7` (github-script).
- `actionlint` was not available in the authoring environment, so the YAML was not
  machine-linted; it follows the standard GitHub Actions schema.
