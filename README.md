# Card Fraud E2E and Load Testing

`card-fraud-e2e-load-testing` is the local-first load harness for card-fraud services.

## Quick Start

```bash
uv sync --extra load-test
uv run lt-rule-engine --users=50 --spawn-rate=10 --run-time=2m --scenario smoke --headless
```

## Core Commands

```bash
uv run lt-run --service all --users=1000 --spawn-rate=100 --run-time=10m --scenario baseline --headless
uv run lt-rule-engine --users=1000 --spawn-rate=100 --run-time=10m --scenario baseline --headless
uv run lt-trans-mgmt --users=200 --spawn-rate=20 --run-time=10m --scenario baseline --headless
uv run lt-rule-mgmt --scenario seed-only --headless
```

## Behavior

- Service selection is controlled by `--service` (`all`, `rule-engine`, `rule-mgmt`, `trans-mgmt`).
- Scenarios are controlled by `--scenario` (`smoke`, `baseline`, `stress`, `soak`, `spike`, `seed-only`).
- Runs use seed -> test -> teardown via `src/utilities/harness.py`.
- Authentication and authorization are assumed to be handled by API Gateway upstream.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `RULE_ENGINE_AUTH_URL` | Rule engine runs | AUTH service base URL (default `http://localhost:8081`) |
| `RULE_ENGINE_MONITORING_URL` | Monitoring runs | MONITORING service base URL (default `http://localhost:8082`) |
| `RULE_ENGINE_URL` | Backward-compatible fallback | Legacy single rule-engine base URL (default `http://localhost:8081`) |
| `RULE_MGMT_URL` | Rule mgmt runs | Rule Management base URL (default `http://localhost:8000`) |
| `TRANSACTION_MGMT_URL` | Trans runs | Transaction Management base URL (default `http://localhost:8002`) |
| `S3_ENDPOINT_URL` | No | MinIO/S3 endpoint (default `http://localhost:9000`) |
| `S3_ACCESS_KEY_ID` | No | S3 access key (default `minioadmin`) |
| `S3_SECRET_ACCESS_KEY` | No | S3 secret key (default `minioadmin`) |
| `S3_BUCKET_NAME` | No | Artifact bucket (default `fraud-gov-artifacts`) |

## Outputs

- Locust HTML/CSV reports in `html-reports/locust/`
- Run summaries in `html-reports/run-summary-*.json` and `.csv`
- Harness metadata in `html-reports/run-metadata-<run_id>.json`
