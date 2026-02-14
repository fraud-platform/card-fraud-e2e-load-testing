# Rule Engine AUTH-only Performance Runs

This document describes how to run AUTH-only performance tests and where the canonical architecture/performance plan lives.

## Canonical plan

The canonical AUTH-only SLO and async durability plan is in the rule-engine repo:
- `card-fraud-rule-engine-auth/docs/04-testing/auth-only-slo-and-async-durability.md`
- `card-fraud-rule-engine-auth/docs/02-development/performance-tuning-plan.md`

## Run AUTH-only

Use the wrapper runner:
- `uv run lt-rule-engine --users=200 --spawn-rate=20 --run-time=2m --scenario baseline --headless`

Latest baseline (2026-02-09):
- Command: `uv run lt-rule-engine --users=100 --spawn-rate=10 --run-time=2m --scenario baseline --headless --skip-seed --skip-teardown`
- Result: p50 `78 ms`, p95 `180 ms`, p99 `600 ms` (SLA not met)

Notes:
- AUTH-only is enforced by wrapper-set weights: `RULE_ENGINE_PREAUTH_WEIGHT=1.0` and `RULE_ENGINE_POSTAUTH_WEIGHT=0.0`.
- Run summary percentiles are taken from Locust aggregate histograms (`stats.total.get_response_time_percentile`).
- Authentication is handled upstream at API Gateway; this harness does not attach JWT per request.

## What to record per run

- users, spawn rate, run time
- scenario name
- service URL
- container CPU and memory limits used for rule-engine
- Redis client pool settings
- per-run Locust artifact paths (HTML and CSV)

These fields are stored in run metadata so regressions are explainable.

