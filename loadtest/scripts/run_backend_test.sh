#!/usr/bin/env bash
#
# One full load-test cycle against an ephemeral AWS stack:
#   apply -> wait healthy -> push k6 image -> steady_state -> stress -> destroy
#
# The stack is destroyed by an EXIT trap, so a failed test still tears it down
# rather than leaving two ALBs and two RDS instances running.
#
# The backend ALB is internal, so it cannot be curled from here: readiness is
# polled through the target-group API, and k6 itself runs as an in-VPC Fargate
# task. See infra/modules/k6_runner.
#
# Needs terraform, aws cli, docker and jq. A local k6 binary is optional and
# only used for the frontend smoke check.
#
#   ./loadtest/scripts/run_backend_test.sh [--skip-apply] [--apply-start-epoch N]
#
# --skip-apply         the stack is already up; confirm with a plan instead of
#                      applying. Pass --apply-start-epoch with the time it
#                      actually went up, or the cost line undercounts.
set -euo pipefail

SKIP_APPLY=0
APPLY_START_EPOCH_OVERRIDE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-apply) SKIP_APPLY=1; shift ;;
    --apply-start-epoch) APPLY_START_EPOCH_OVERRIDE="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRA_DIR="$REPO_ROOT/infra"
RESULTS_DIR="$REPO_ROOT/loadtest/results"
mkdir -p "$RESULTS_DIR"

log() { echo "[run_backend_test] $*"; }

DESTROY_ON_EXIT=0
K6_RUNTIME_SECONDS=0
APPLY_START_EPOCH=""

cleanup() {
  local status=$?
  if [ "$DESTROY_ON_EXIT" -eq 1 ]; then
    log "tearing the stack down"
    terraform -chdir="$INFRA_DIR" destroy -auto-approve -var="force_destroy=true" || {
      log "DESTROY FAILED. The stack is still running and still costing money."
      log "Run: terraform -chdir=$INFRA_DIR destroy -auto-approve -var=\"force_destroy=true\""
      exit 1
    }
    DESTROY_ON_EXIT=0
    if [ -n "$APPLY_START_EPOCH" ]; then
      python3 "$REPO_ROOT/loadtest/scripts/estimate_cost.py" \
        --start "$APPLY_START_EPOCH" --end "$(date +%s)" --k6-seconds "$K6_RUNTIME_SECONDS" \
        | tee "$RESULTS_DIR/cost.md"
    fi
  fi
  exit "$status"
}
trap cleanup EXIT

log "terraform init"
terraform -chdir="$INFRA_DIR" init -input=false

if [ "$SKIP_APPLY" -eq 1 ]; then
  APPLY_START_EPOCH="${APPLY_START_EPOCH_OVERRIDE:-$(date +%s)}"
  if [ -z "$APPLY_START_EPOCH_OVERRIDE" ]; then
    log "WARNING: --skip-apply without --apply-start-epoch, the cost line will undercount"
  fi
  log "confirming the live stack matches this config"
  if ! terraform -chdir="$INFRA_DIR" plan -input=false -detailed-exitcode -var="force_destroy=true" >/tmp/k6-plan.log 2>&1; then
    code=$?
    if [ "$code" -eq 2 ]; then
      log "the live stack does not match this config, see /tmp/k6-plan.log"
    else
      log "terraform plan failed with $code, see /tmp/k6-plan.log"
    fi
    exit 1
  fi
else
  APPLY_START_EPOCH=$(date +%s)
  log "terraform apply"
  terraform -chdir="$INFRA_DIR" apply -auto-approve -var="force_destroy=true"
  DESTROY_ON_EXIT=1
fi

tf_output() { terraform -chdir="$INFRA_DIR" output -raw "$1"; }

ALB_DNS=$(tf_output alb_dns_name)
TARGET_GROUP_ARN=$(tf_output backend_target_group_arn)
K6_ECR_URL=$(tf_output k6_ecr_repository_url)
K6_CLUSTER=$(tf_output k6_cluster_name)
K6_TASK_DEF=$(tf_output k6_task_definition_family)
K6_SG=$(tf_output k6_task_security_group_id)
K6_LOG_GROUP=$(tf_output k6_log_group_name)
FRONTEND_URL=$(tf_output frontend_alb_url)
REGION=$(tf_output region)
SUBNETS_JSON=$(terraform -chdir="$INFRA_DIR" output -json app_subnet_ids)

log "waiting for the backend target group to report healthy"
for i in $(seq 1 30); do
  HEALTHY=$(aws elbv2 describe-target-health --target-group-arn "$TARGET_GROUP_ARN" \
    --query "length(TargetHealthDescriptions[?TargetHealth.State=='healthy'])" --output text)
  if [ "$HEALTHY" -ge 1 ]; then
    log "backend healthy ($HEALTHY target(s))"
    break
  fi
  if [ "$i" -eq 30 ]; then
    log "backend never became healthy"
    exit 1
  fi
  log "not healthy yet ($HEALTHY), retrying in 10s ($i/30)"
  sleep 10
done

log "pushing the k6 image to $K6_ECR_URL"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${K6_ECR_URL%/*}"
docker build -t "$K6_ECR_URL:latest" "$REPO_ROOT/loadtest/k6"
docker push "$K6_ECR_URL:latest"

run_k6_task() {
  local script_name="$1"
  local out_file="$RESULTS_DIR/${script_name%.js}.log"
  local overrides task_start task_end task_arn task_id exit_code

  log "launching k6 task: $script_name"
  overrides=$(jq -n --arg script "/scripts/$script_name" --arg target "http://$ALB_DNS/api/v1" '{
    containerOverrides: [{
      name: "k6",
      command: ["run", $script],
      environment: [{name: "TARGET_URL", value: $target}]
    }]
  }')

  task_start=$(date +%s)
  task_arn=$(aws ecs run-task \
    --cluster "$K6_CLUSTER" \
    --task-definition "$K6_TASK_DEF" \
    --launch-type FARGATE \
    --network-configuration "{\"awsvpcConfiguration\":{\"subnets\":$SUBNETS_JSON,\"securityGroups\":[\"$K6_SG\"],\"assignPublicIp\":\"DISABLED\"}}" \
    --overrides "$overrides" \
    --query 'tasks[0].taskArn' --output text)
  task_id="${task_arn##*/}"
  log "task $task_id started, waiting for it to stop"

  aws ecs wait tasks-stopped --cluster "$K6_CLUSTER" --tasks "$task_arn"
  task_end=$(date +%s)
  K6_RUNTIME_SECONDS=$((K6_RUNTIME_SECONDS + task_end - task_start))

  exit_code=$(aws ecs describe-tasks --cluster "$K6_CLUSTER" --tasks "$task_arn" \
    --query 'tasks[0].containers[0].exitCode' --output text)
  log "task stopped with exit code $exit_code"

  aws logs get-log-events --log-group-name "$K6_LOG_GROUP" --log-stream-name "k6/k6/$task_id" \
    --query 'events[*].message' --output text > "$out_file"
  log "summary saved to $out_file"
}

run_k6_task "steady_state.js"
run_k6_task "stress.js"

if command -v k6 >/dev/null 2>&1; then
  log "smoke-testing the frontend from here"
  k6 run -e TARGET_URL="$FRONTEND_URL" "$REPO_ROOT/loadtest/k6/smoke_frontend.js" \
    | tee "$RESULTS_DIR/smoke_frontend.log"
else
  log "k6 not installed locally, skipping the frontend smoke check"
  log "run it yourself: k6 run -e TARGET_URL=$FRONTEND_URL loadtest/k6/smoke_frontend.js"
fi

log "done, results in $RESULTS_DIR"
