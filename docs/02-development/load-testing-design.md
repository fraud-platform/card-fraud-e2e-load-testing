# Load Testing Design Document

Project: `card-fraud-e2e-load-testing`  
Version: 1.3  
Date: 2026-02-03

---

## 1. Overview

This document describes the current technical design for local-first E2E and load testing across card fraud services.

### 1.1 Services Under Test

| Service | Framework | Load Priority | Throughput Intent | P99 Latency Intent |
|---|---|---|---|---|
| Rule Engine | Quarkus/Java | High | 10,000+ RPS | < 50ms |
| Transaction Management | FastAPI/Python | Medium (local target) | ~50 TPS local target | relaxed/local-context |
| Rule Management | FastAPI/Python | Low | ~50 TPS local target | relaxed/local-context |

### 1.2 Design Principles

1. Unified suite for all services
2. Configurable workload by service and scenario
3. Synthetic-only data (never real PAN/PII)
4. Idempotent lifecycle: seed -> test -> teardown
5. Explicit auth behavior (`none`, `auth0`, `local`)
6. Local-first execution against real containers where possible

Related operational plan: `docs/ENTERPRISE-LOCAL-LOAD-TEST-PLAN.md`.

---

## 2. Technology Stack

| Tool | Version/Range | Purpose |
|---|---|---|
| Locust | 2.29.1 | Load framework |
| Python | 3.14+ | Runtime |
| pytest | 8.3+ | Test framework |
| pytest-html | 4.1+ | Test report output |
| Faker | 33.0+ | Synthetic data generation |
| boto3 | 1.42.39+ | S3/MinIO operations |
| httpx | 0.27+ | HTTP preflight/auth calls |

---

## 3. Current Repository Structure

```text
card-fraud-e2e-load-testing/
|-- AGENTS.md
|-- claude.md
|-- README.md
|-- docker-compose.yml
|-- pyproject.toml
|-- docs/
|   |-- LOAD-TESTING-DESIGN.md
|   `-- ENTERPRISE-LOCAL-LOAD-TEST-PLAN.md
|-- scripts/
|   |-- run_load_test.py
|   |-- generate_report.py
|   |-- generate_users.py
|   |-- generate_transactions.py
|   |-- generate_rules.py
|   `-- generate_rulesets.py
|-- src/
|   |-- locustfile.py
|   |-- auth/auth0.py
|   |-- config/defaults.py
|   |-- generators/__init__.py
|   |-- tasksets/rule_engine/
|   |-- tasksets/rule_management/
|   |-- tasksets/transaction_mgmt/
|   `-- utilities/
`-- tests/
    `-- __init__.py
```

---

## 4. Service Configurations

Service configs are centralized in `src/config/defaults.py`.

### 4.1 Rule Engine

- Config class: `RuleEngineConfig`
- Traffic mix defaults: PREAUTH `70%`, POSTAUTH `30%`
- Threshold intent: p99 `< 50ms`, error rate `< 1%`

### 4.2 Transaction Management

- Config class: `TransactionManagementConfig`
- Traffic mix defaults: ingestion `40%`, list `40%`, detail `20%`
- Threshold intent: p99 `< 200ms`, error rate `< 1%`

### 4.3 Rule Management

- Config class: `RuleManagementConfig`
- Governance-focused, lower-throughput intent
- Threshold intent: p99 `< 500ms`, error rate `< 1%`

---

## 5. Data Generation Design

### 5.1 CLI Data Generators

- `gen-transactions`
- `gen-users`
- `gen-rules`
- `gen-rulesets`

### 5.2 Programmatic Generators (`src/generators/__init__.py`)

```python
from src.generators import TransactionGenerator, UserGenerator, RuleGenerator

tx = TransactionGenerator(seed=42).generate()
user = UserGenerator(seed=42).generate()
rule = RuleGenerator(seed=42).generate(rule_type="PREAUTH")
ruleset = RuleGenerator(seed=42).generate_ruleset(ruleset_type="PREAUTH")
```

### 5.3 Data Constraints

- Synthetic-only values
- Masked/tokenized card identifiers in payloads
- Reproducible generation via seed
- Risk-level distributions for transactions

---

## 6. Running Load Tests

### 6.1 Interactive UI

```bash
uv run lt-web
# Locust UI: http://localhost:8089
```

### 6.2 CLI Runner

```bash
# Rule Engine
uv run lt-rule-engine --users=1000 --spawn-rate=100 --run-time=10m --scenario baseline --auth-mode none

# Transaction Management
uv run lt-trans-mgmt --users=200 --spawn-rate=20 --run-time=10m --scenario baseline --auth-mode none

# Rule Management
uv run lt-rule-mgmt --users=50 --spawn-rate=10 --run-time=10m --scenario baseline --auth-mode none

# All services
uv run lt-run --service all --users=1000 --spawn-rate=100 --run-time=10m --scenario baseline --auth-mode none
```

### 6.3 Preflight Health Checks

The runner validates target service health before starting Locust:

- Rule Engine: `/v1/evaluate/health`
- Rule Management: `/api/v1/health`
- Transaction Management: `/api/v1/health`

---

## 7. Scenarios

Scenarios in `src/config/defaults.py` and `scripts/run_load_test.py`:

- `smoke`
- `baseline`
- `stress`
- `soak`
- `spike`
- `seed-only`

Example:

```bash
uv run lt-rule-engine --scenario stress --users=1000 --spawn-rate=100 --run-time=10m
```

(Scenario logic may override user/spawn/time values per runner rules.)

---

## 8. Auth Modes

Supported via `--auth-mode`:

- `none`: no auth header
- `auth0`: Auth0 client credentials (token cache)
- `local`: locally signed token

Auth implementation: `src/auth/auth0.py`.

---

## 9. Seed/Test/Teardown Harness

`LoadTestHarness` (`src/utilities/harness.py`) provides:

1. run ID generation/override
2. optional seed phase
3. optional teardown phase
4. run metadata output

Control flags:

- `--skip-seed`
- `--skip-teardown`
- `--run-id <id>`

Run metadata output:

- `html-reports/run-metadata-<run_id>.json`

---

## 10. Reporting

### 10.1 Automatic per-run outputs

- `html-reports/run-summary-<timestamp>.json`
- `html-reports/run-summary-<timestamp>.csv`
- Locust HTML/CSV outputs under `html-reports/locust/`

### 10.2 Combined reports

```bash
uv run gen-report
uv run gen-report --runs=20260203-071848,20260203-071049
```

Default combined outputs:

- `html-reports/combined/index.html`
- `html-reports/combined/report.md`

---

## 11. Environment Variables

| Variable | Required | Default/Notes |
|---|---|---|
| `RULE_ENGINE_URL` | Rule-engine runs | `http://localhost:8081` |
| `RULE_MGMT_URL` | Rule-mgmt runs | `http://localhost:8000` |
| `TRANSACTION_MGMT_URL` | Trans runs | `http://localhost:8002` |
| `AUTH_MODE` | No | `none`, `auth0`, `local` |
| `AUTH0_DOMAIN` | For `auth0` | none |
| `AUTH0_AUDIENCE` | For `auth0` | none |
| `AUTH0_CLIENT_ID` | For `auth0` | none |
| `AUTH0_CLIENT_SECRET` | For `auth0` | none |
| `LOCAL_SIGNING_KEY` | For `local` | optional |
| `S3_ENDPOINT_URL` | No | `http://localhost:9000` |
| `S3_ACCESS_KEY_ID` | No | `minioadmin` |
| `S3_SECRET_ACCESS_KEY` | No | `minioadmin` |
| `S3_BUCKET_NAME` | No | `fraud-gov-artifacts` |

Fallback compatibility variables remain supported:
`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_SECURE`.

---

## 12. Monitoring Status

- Compose includes Prometheus/Grafana containers.
- Full local wiring/provisioning files are not complete in this repo yet.
- Treat monitoring stack as optional scaffolding at current state.

---

## 13. CI/CD Status

CI/CD workflows are intentionally deferred at this stage; local reproducibility is the primary path.

---

## 14. Key Metrics and Threshold Intent

### Rule Engine

- Throughput intent: 10,000+ RPS
- Latency intent: p99 < 50ms
- Error rate intent: < 1%

### Transaction Management

- Local throughput target: ~50 TPS
- Latency intent: p99 < 200ms
- Error rate intent: < 1%

### Rule Management

- Local throughput target: ~50 TPS
- Latency intent: p99 < 500ms
- Error rate intent: < 1%

---

## 15. Implementation Status Snapshot

Implemented:

- Load commands (`lt-run`, `lt-web`, service wrappers)
- Auth modes (`none`, `auth0`, `local`)
- Scenario support (`smoke`, `baseline`, `stress`, `soak`, `spike`, `seed-only`)
- Seed/test/teardown harness with run metadata
- MinIO artifact publish/cleanup utilities
- Data generation CLIs
- Combined report generation

Planned/partial:

- Full Prometheus/Grafana provisioning in-repo
- CI workflow automation in-repo
- More strict automated threshold gates for all service classes

---

Document Version: 1.3  
Last Updated: 2026-02-03
