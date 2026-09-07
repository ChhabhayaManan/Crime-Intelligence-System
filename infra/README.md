# Infrastructure

Terraform for the whole stack. `terraform fmt -check -recursive` and
`terraform validate` both pass; CI runs them on every change to `infra/**`.

The modules are named after what they build, so this file only covers the
decisions you cannot read off the code.

## Two ALBs, and the backend one is internal

`modules/alb` is **internal**. Only the frontend ECS tasks and the k6 runner
can reach it, from inside the VPC. `modules/frontend_alb` is the
internet-facing one, and it is the only public entrypoint.

Two things follow from that:

- CI cannot HTTP-probe the backend after a deploy. It polls target-group
  health through the ELB API instead, which is equivalent because the target
  group's own health check hits `GET /health` on each task.
- The load test cannot run from a laptop. `modules/k6_runner` puts k6 in the
  backend's private app subnets as a one-off Fargate task.

## Cross-module security group rules live in the root

`main.tf` holds four `aws_security_group_rule` resources rather than putting
them in the modules that own the security groups. The frontend and k6 modules
need rules on the alb and endpoints security groups, and those modules would
then depend on frontend, which already depends on them. Terraform rejects the
cycle. Hoisting the rules to the root breaks it.

## IAM builds some ARNs as strings

`modules/iam` writes ECS cluster, service and task-definition ARNs by hand
instead of referencing `module.ecs`. Same reason: ecs needs the roles that iam
creates, so iam cannot reference ecs back. The names are deterministic, so the
strings are safe, but renaming anything in `modules/ecs` means updating the
locals in `modules/iam/main.tf` too.

## The terraform role is broad on purpose

`github_actions_terraform` grants `ec2:*`, `iam:*`, `s3:*` and friends on
`*`. A tool that provisions resources cannot be scoped to ARNs that do not
exist yet. Worth knowing that this is effectively an admin role, and that any
pull request against `infra/**` can assume it for a plan.

The two runtime roles are properly scoped: the task role reaches exactly one
S3 bucket, and the execution role reaches exactly the three ECR repos, three
log groups and two secrets it needs.

## No autoscaling

`desired_count` is fixed at 2 for both tiers. That is deliberate: the load
test is measuring a known, fixed capacity. `application-autoscaling:*` is
granted but nothing uses it yet.

## Private subnets have no NAT

`modules/endpoints` provides interface endpoints for ECR and CloudWatch Logs
plus an S3 gateway endpoint. ECR layer blobs travel over the S3 gateway,
which is why every task security group needs egress to the S3 prefix list as
well as to the interface endpoints.
