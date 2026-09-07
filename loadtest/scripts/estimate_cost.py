#!/usr/bin/env python3
"""
Cost estimate for one ephemeral load-test run, in USD.

Forecast before spending anything (default), so you can see the run against
your remaining credit:

    python loadtest/scripts/estimate_cost.py --hours 1.5

Or price a run that already happened:

    python loadtest/scripts/estimate_cost.py --start <epoch> --end <epoch> --k6-seconds 900

Prices are ap-south-1 on-demand list prices, hardcoded. Treat the total as an
upper bound for planning, not a bill.
"""
import argparse
from datetime import datetime, timezone

FARGATE_VCPU_HOUR = 0.04256
FARGATE_GB_HOUR = 0.004655
RDS_DB_T3_MICRO_HOUR = 0.026
ALB_HOUR = 0.0239

BACKEND_TASKS, BACKEND_VCPU, BACKEND_GB = 2, 0.25, 0.5
FRONTEND_TASKS, FRONTEND_VCPU, FRONTEND_GB = 2, 0.25, 0.5
K6_VCPU, K6_GB = 1.0, 2.0
RDS_INSTANCES = 2
ALB_COUNT = 2

MISC_BUFFER_USD = 0.05
CREDIT_USD = 70.0
K6_TEST_MINUTES = 20


def breakdown(stack_hours, k6_hours):
    backend = BACKEND_TASKS * (BACKEND_VCPU * FARGATE_VCPU_HOUR + BACKEND_GB * FARGATE_GB_HOUR) * stack_hours
    frontend = FRONTEND_TASKS * (FRONTEND_VCPU * FARGATE_VCPU_HOUR + FRONTEND_GB * FARGATE_GB_HOUR) * stack_hours
    k6 = (K6_VCPU * FARGATE_VCPU_HOUR + K6_GB * FARGATE_GB_HOUR) * k6_hours
    return [
        ("Backend Fargate (2x 0.25vCPU/0.5GB)", backend),
        ("Frontend Fargate (2x 0.25vCPU/0.5GB)", frontend),
        ("k6 runner Fargate (1vCPU/2GB, test duration only)", k6),
        ("RDS db.t3.micro writer + reader", RDS_INSTANCES * RDS_DB_T3_MICRO_HOUR * stack_hours),
        ("2x Application Load Balancer", ALB_COUNT * ALB_HOUR * stack_hours),
        ("S3 / Secrets Manager / Logs (buffer)", MISC_BUFFER_USD),
    ]


def report(title, stack_hours, k6_hours, note):
    rows = breakdown(stack_hours, k6_hours)
    total = sum(cost for _, cost in rows)

    print(f"\n{title}")
    print(f"{note}\n")
    print("| Component | USD |")
    print("|---|---|")
    for label, cost in rows:
        print(f"| {label} | ${cost:.4f} |")
    print(f"| **Total** | **${total:.4f}** |")
    print(f"\nCredit: ${CREDIT_USD:.2f}. This run is {total / CREDIT_USD * 100:.1f}% of it, "
          f"leaving ${CREDIT_USD - total:.2f} for roughly {int(CREDIT_USD / total) - 1} more runs of this length.")
    return total


def main():
    parser = argparse.ArgumentParser(description="Estimate the cost of a load-test run.")
    parser.add_argument("--hours", type=float, help="planned stack lifetime, apply to destroy")
    parser.add_argument("--start", type=int, help="actual apply start, unix epoch")
    parser.add_argument("--end", type=int, help="actual destroy finish, unix epoch")
    parser.add_argument("--k6-seconds", type=float, default=0.0, help="seconds the k6 tasks ran")
    args = parser.parse_args()

    if args.start and args.end:
        stack_hours = max(args.end - args.start, 0) / 3600
        k6_hours = max(args.k6_seconds, 0) / 3600
        started = datetime.fromtimestamp(args.start, tz=timezone.utc)
        finished = datetime.fromtimestamp(args.end, tz=timezone.utc)
        report(
            f"## Load test run - {started.date()}",
            stack_hours,
            k6_hours,
            f"Actual window {started.isoformat()} to {finished.isoformat()} "
            f"({stack_hours:.2f}h stack, {k6_hours * 60:.0f} min of k6).",
        )
        return

    stack_hours = args.hours if args.hours else 1.5
    k6_hours = K6_TEST_MINUTES / 60
    report(
        "## Load test forecast",
        stack_hours,
        k6_hours,
        f"Assuming the stack is up {stack_hours:.2f}h and k6 runs {K6_TEST_MINUTES} min. "
        "Pass --hours to change it.",
    )


if __name__ == "__main__":
    main()
