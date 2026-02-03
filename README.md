# Card Fraud E2E and Load Testing

`card-fraud-e2e-load-testing` is the local-first E2E and load testing suite for the card fraud platform.

It targets three services:

| Service | Stack | Load Priority | Local Target |
|---|---|---|---|
| Rule Engine | Quarkus/Java | High | 10,000+ RPS, P50 < 5ms, P95 < 15ms, P99 < 30ms |
| Transaction Management | FastAPI/Python | Medium | ~50 TPS local target |
| Rule Management | FastAPI/Python | Low | ~50 TPS local target |

## Quick Start

### Prerequisites

- Python `3.14+`
- `uv`
- Target services running locally (typically via the platform repository)

```bash
# Install dependencies
uv sync --extra load-test

# Quick smoke (Rule Engine only)
uv run lt-rule-engine --users=50 --spawn-rate=10 --run-time=2m --scenario smoke --auth-mode none
```

## Command Reference

### Load Test Commands

| Command | Purpose |
|---|---|
| `uv run lt-run` | Run load test runner (default `--service all`) |
| `uv run lt-web` | Start Locust web UI on `http://localhost:8089` |
| `uv run lt-rule-engine` | Wrapper for `lt-run --service rule-engine` |
| `uv run lt-trans-mgmt` | Wrapper for `lt-run --service trans-mgmt` |
| `uv run lt-rule-mgmt` | Wrapper for `lt-run --service rule-mgmt` |

Examples:

```bash
# Baseline all services
uv run lt-run --service all --users=1000 --spawn-rate=100 --run-time=10m --scenario baseline --auth-mode none

# Rule Engine only
uv run lt-rule-engine --users=1000 --spawn-rate=100 --run-time=10m --scenario baseline --auth-mode none

# Transaction Management only
uv run lt-trans-mgmt --users=200 --spawn-rate=20 --run-time=10m --scenario baseline --auth-mode none

# Rule Management seed-only
uv run lt-rule-mgmt --scenario seed-only --auth-mode auth0

# Keep seeded artifacts for inspection
uv run lt-rule-engine --users=1000 --skip-teardown

# Custom run id
uv run lt-rule-engine --users=1000 --run-id my-test-run-42
```

### Data Generation Commands

| Command | Purpose |
|---|---|
| `uv run gen-users` | Generate synthetic users |
| `uv run gen-transactions` | Generate synthetic transactions |
| `uv run gen-rules` | Generate synthetic rules |
| `uv run gen-rulesets` | Generate synthetic rulesets |

Examples:

```bash
uv run gen-users --count=1000 --output=fixtures/users.json
uv run gen-transactions --count=10000 --distribution normal:0.8,high:0.15,suspicious:0.05 --output=fixtures/transactions.json
uv run gen-rules --count=100 --rule-type PREAUTH --output=fixtures/rules.json
uv run gen-rulesets --count=10 --rules-per-set=20 --output=fixtures/rulesets.json
```

### Report Commands

```bash
# Combine all discovered run-summary files from html-reports/
uv run gen-report

# Combine specific runs
uv run gen-report --runs=20260203-071848,20260203-071049
```

`gen-report` arguments:

- `--reports-dir` (default: `html-reports`)
- `--output` (default: `html-reports/combined/index.html`)
- `--markdown-output` (default: `html-reports/combined/report.md`)

## Runtime Behavior

### Service Selection

`lt-run` accepts `--service` values:

- `all`
- `rule-engine`
- `rule-mgmt`
- `trans-mgmt`

Wrapper scripts (`lt-rule-engine`, `lt-rule-mgmt`, `lt-trans-mgmt`) inject this automatically.

### Scenarios

Supported scenarios:

- `smoke`
- `baseline`
- `stress`
- `soak`
- `spike`
- `seed-only`

The runner applies scenario-specific user/spawn/duration overrides in `scripts/run_load_test.py`.

### Seed -> Test -> Teardown Lifecycle

Each run is managed by `LoadTestHarness` (`src/utilities/harness.py`):

1. Generate/select `run_id`
2. Seed artifacts (if enabled)
3. Execute Locust test
4. Teardown artifacts (if enabled)
5. Write run metadata to `html-reports/run-metadata-{run_id}.json`

## Authentication Modes

`--auth-mode` supports:

- `none`: no `Authorization` header
- `auth0`: Auth0 client credentials token (cached in-process)
- `local`: locally signed development token

### Local JWT Bypass (service-side)

For local-only testing without Auth0 rate limits, API services can be configured with:

```bash
APP_ENV=local
SECURITY_SKIP_JWT_VALIDATION=true
```

Then run tests with `--auth-mode none`.

Security expectation: bypass must remain local-only.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `RULE_ENGINE_URL` | Yes | Rule Engine base URL (default `http://localhost:8081`) |
| `RULE_MGMT_URL` | Rule mgmt tests | Rule Management base URL (default `http://localhost:8000`) |
| `TRANSACTION_MGMT_URL` | Trans tests | Transaction Management base URL (default `http://localhost:8002`) |
| `AUTH_MODE` | No | `none`, `auth0`, or `local` |
| `AUTH0_DOMAIN` | For `auth0` | Auth0 domain |
| `AUTH0_AUDIENCE` | For `auth0` | Auth0 audience |
| `AUTH0_CLIENT_ID` | For `auth0` | Auth0 client id |
| `AUTH0_CLIENT_SECRET` | For `auth0` | Auth0 client secret |
| `LOCAL_SIGNING_KEY` | For `local` | Optional signing key for local JWT |
| `S3_ENDPOINT_URL` | No | MinIO/S3 endpoint (default `http://localhost:9000`) |
| `S3_ACCESS_KEY_ID` | No | S3 access key (default `minioadmin`) |
| `S3_SECRET_ACCESS_KEY` | No | S3 secret key (default `minioadmin`) |
| `S3_BUCKET_NAME` | No | Artifact bucket (default `fraud-gov-artifacts`) |

Backward-compatible fallback variables are still accepted by the MinIO client:

- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_SECURE`

## Reports and Outputs

Generated outputs:

- Locust HTML/CSV files in `html-reports/locust/`
- Run summaries from Locust stop hook:
  - `html-reports/run-summary-<timestamp>.json`
  - `html-reports/run-summary-<timestamp>.csv`
- Harness run metadata:
  - `html-reports/run-metadata-<run_id>.json`
- Combined report:
  - `html-reports/combined/index.html`
  - `html-reports/combined/report.md`

## Project Structure

```text
card-fraud-e2e-load-testing/
|-- AGENTS.md
|-- claude.md
|-- README.md
|-- docker-compose.yml
|-- pyproject.toml
|-- docs/
|   |-- ENTERPRISE-LOCAL-LOAD-TEST-PLAN.md
|   `-- LOAD-TESTING-DESIGN.md
|-- scripts/
|   |-- run_load_test.py
|   |-- generate_users.py
|   |-- generate_transactions.py
|   |-- generate_rules.py
|   |-- generate_rulesets.py
|   `-- generate_report.py
|-- src/
|   |-- auth/auth0.py
|   |-- config/defaults.py
|   |-- generators/__init__.py
|   |-- locustfile.py
|   |-- tasksets/rule_engine/
|   |-- tasksets/rule_management/
|   |-- tasksets/transaction_mgmt/
|   `-- utilities/
`-- tests/
    `-- __init__.py
```

## Monitoring and CI Status

- `docker-compose.yml` defines Prometheus/Grafana containers, but this repository currently does not include ready-to-run Prometheus config/provisioning files.
- CI/CD workflows are not yet committed in this repo (local-first execution is the active path).

## Troubleshooting

| Issue | What to check |
|---|---|
| Service health check fails | Verify target service URL and health endpoint |
| Auth errors in `auth0` mode | Validate `AUTH0_*` values |
| `429` or saturation | Lower `--spawn-rate` / users |
| Missing combined report data | Confirm `run-summary-*.json` exists in `html-reports/` |
| MinIO upload failures | Verify `S3_*` or `MINIO_*` configuration and bucket access |

## Additional Docs

- Detailed design: `docs/LOAD-TESTING-DESIGN.md`
- Enterprise local execution plan: `docs/ENTERPRISE-LOCAL-LOAD-TEST-PLAN.md`
- Agent playbook: `AGENTS.md`
