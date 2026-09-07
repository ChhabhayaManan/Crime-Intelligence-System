# Load Testing (k6)

Load-tests the FastAPI backend against a real, ephemeral AWS deployment
(2x Fargate tasks, 256cpu/512mem, no autoscaling, RDS db.t3.micro), plus a
light smoke check of the Streamlit tier.

## Layout

```
k6/
  lib.js               shared setup() + 80/20 read/write traffic mix
  steady_state.js      50 VU, 8 min - the headline number
  stress.js            staged ramp to 300 VU - finds the breaking point
  smoke_frontend.js    20 VU, 1 min against the public frontend ALB
  Dockerfile           grafana/k6 + scripts, pushed to the cis-k6 ECR repo
scripts/
  run_backend_test.sh  apply -> test -> destroy
  estimate_cost.py     what a run costs, before or after
results/               per-run k6 log dumps (gitignored)
```

## What a run costs

Check before you spend anything:

```bash
python loadtest/scripts/estimate_cost.py --hours 1.5
```

A 1.5 hour run is roughly **$0.30** - about 0.4% of a $70 credit, so the
credit covers a couple of hundred runs of that length. Almost all of it is
the two ALBs and the two RDS instances sitting there; the k6 task itself is
cents. The number that actually matters is how long the stack stays up, so
the one expensive mistake is leaving it running.

`run_backend_test.sh` destroys the stack from an `EXIT` trap, so a failed
test still tears it down. If the destroy itself fails the script says so
loudly and tells you the command to run.

## Running a test

```bash
./loadtest/scripts/run_backend_test.sh
```

Applies the stack, waits for the backend target group to go healthy, pushes
the k6 image, runs `steady_state.js` then `stress.js` as one-off Fargate
tasks in the backend's private subnets, smoke-tests the frontend from your
machine, then destroys everything and writes the actual cost to
`loadtest/results/cost.md`.

If the stack is already up (pushing `infra/**` to `main` auto-applies):

```bash
./loadtest/scripts/run_backend_test.sh --skip-apply --apply-start-epoch <epoch when it went up>
```

`--skip-apply` runs a `terraform plan` first and aborts if the live stack
does not match the checked-out config. It does **not** destroy the stack on
exit, since it did not create it.

Needs `terraform`, AWS CLI, `docker`, `jq`. A local `k6` binary is optional
and only used for the frontend smoke check.

## Reading the results

- `results/steady_state.log`, `results/stress.log` - k6's end-of-run summary
  (req/s, latency percentiles, threshold pass/fail) pulled from CloudWatch.
- `stress.js` uses `abortOnFail`, so it stops the moment p95 latency or the
  error rate breaches the SLO instead of running the full 12 minutes. Read it
  next to CloudWatch Container Insights and RDS metrics for the same window
  to see which tier gave out first.
- `setup()` aborts the run outright if it cannot register, log in, or find
  seed data. A run that authenticates badly would otherwise finish green
  while measuring nothing but 401s.
- Confirm the cost the next day, since Cost Explorer lags about 24h:
  ```bash
  aws ce get-cost-and-usage --time-period Start=<date>,End=<date+1> \
    --granularity DAILY --metrics UnblendedCost
  ```
