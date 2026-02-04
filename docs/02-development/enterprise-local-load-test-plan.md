# Enterprise Local Load Testing Plan (Locust)

Date: 2026-02-03

This document defines the enterprise-grade, production-like (synthetic) local load testing strategy for this repository.

Scope is local-first (Docker Desktop + platform compose). CI/CD can be added later without changing test semantics.

---

## 1. Goals

- Run real E2E load tests against real local service containers.
- Use synthetic but production-like traffic patterns.
- Keep runs repeatable and idempotent via seed -> test -> teardown.
- Support one-service or all-service runs from one command family.
- Support JWT behavior explicitly with `AUTH_MODE`/`--auth-mode`.
- Produce actionable report artifacts.

---

## 2. Non-Goals (Current Phase)

- Distributed load generators at production scale
- Full CI/CD automation in this repo
- Changes to production service code for test-only behavior

---

## 3. System Context and Assumptions

### Repositories (organization context)

- `card-fraud-platform`: local infra and compose orchestration
- `card-fraud-rule-engine`: high-priority decisioning engine
- `card-fraud-rule-management`: governance API and artifact publication
- `card-fraud-transaction-management`: transaction ingestion/query API
- `card-fraud-e2e-load-testing` (this repo): load scenarios, harness, reporting

### Local Infrastructure

- Docker Desktop hosts containers
- MinIO serves as local S3-compatible storage
- Doppler (or equivalent env provisioning) is recommended; no committed secrets

### Artifact Flow

- Rule-management publishes rulesets/artifacts to MinIO/S3
- Rule-engine consumes artifacts (startup/polling behavior owned by service repos)

---

## 4. Repository Responsibilities

### This repo owns

- Seed/teardown workflows
- Load profiles and scenarios
- Runner and harness logic
- Result reporting and summaries

### Platform repo owns

- Compose topology
- Dependency containers and networking
- Local start/stop orchestration

---

## 5. Execution Model

Recommended topology:

- Services in local containers
- Load tests invoked from this repo with `uv run ...`

This keeps network hops, container resource constraints, DB behavior, and storage paths realistic.

---

## 6. Auth Strategy (JWT On/Off)

Supported modes:

- `AUTH_MODE=none`
  - Send no auth header
  - Useful when local bypass is enabled in target service

- `AUTH_MODE=auth0`
  - Auth0 client credentials flow
  - Token cache required to avoid auth provider pressure

- `AUTH_MODE=local`
  - Locally signed token for dev-only compatible services
  - Fail fast when service does not accept local token

---

## 7. Idempotent Seed/Test/Teardown

Every run has a `run_id`.

Tag/prefix expectations:

- MinIO keys: `loadtest/{run_id}/...`
- Run metadata file: `html-reports/run-metadata-{run_id}.json`

Default behavior:

- Seed enabled
- Teardown enabled

Flags:

- `--skip-seed`
- `--skip-teardown`
- `--run-id`

---

## 8. Data Strategy (Synthetic, Production-like)

Principles:

- No real card numbers
- No real PII
- No production data copies

Modeling intent:

- Non-uniform risk/amount distributions
- Correlation (card, merchant, geography)
- Mixed behavioral patterns (steady + burst-like)

Current implementation includes deterministic seeds and risk distributions in generator scripts.

---

## 9. Scenario Taxonomy

Each scenario should define load shape + runtime intent + quality expectations.

Current supported scenarios:

- `smoke`
- `baseline`
- `stress`
- `soak`
- `spike`
- `seed-only`

---

## 10. Service Workloads and SLO Focus

### Rule Engine (High Priority)

- Primary objective: low-latency decisioning under high throughput
- Default mix: PREAUTH-heavy, POSTAUTH-secondary
- Tightest latency/error expectations

### Transaction Management (Medium Priority)

- Local target around ~50 TPS
- Focus on ingestion + query behavior

### Rule Management (Low Priority)

- Governance operations and artifact lifecycle
- Lower throughput than core decisioning path

---

## 11. Harness Responsibilities

Harness must:

- Validate auth setup for selected mode
- Validate/execute seed workflows
- Run test with consistent run identity
- Execute teardown cleanup
- Persist run metadata

Implementation reference: `src/utilities/harness.py`.

---

## 12. Reporting and Quality Gates

Required outputs per run:

- Locust HTML + CSV
- JSON and CSV run summary files
- Optional combined report across runs

Current pass/fail behavior:

- Locust quit handler and report generation mark failure when fail ratio exceeds configured threshold behavior in code.

Future tightening:

- Stronger explicit SLO gates per service/scenario

---

## 13. Operator Experience (Humans and Agents)

One-command style examples:

```bash
# Baseline rule engine without JWT
doppler run -- uv run lt-rule-engine --scenario baseline --auth-mode none

# Baseline rule engine with Auth0
doppler run -- uv run lt-rule-engine --scenario baseline --auth-mode auth0

# Seed-only rule management workflow
doppler run -- uv run lt-rule-mgmt --scenario seed-only --auth-mode auth0

# Baseline all services
doppler run -- uv run lt-run --service all --scenario baseline --auth-mode auth0
```

Safety expectations:

- Never run against production
- Never log tokens/secrets
- Mask sensitive identifiers in logs and reports

---

## 14. Implementation Roadmap (Local-first)

| Phase | Status | Description |
|---|---|---|
| Phase 0 | Complete | Runnable baseline and command consistency |
| Phase 1 | Complete | Seed/teardown harness + MinIO artifact flow |
| Phase 2 | In Progress | Stronger enterprise workload realism and gates |
| Phase 3 | Not Started | Optional observability hardening |
| Phase 4 | Not Started | CI/CD integration |

### Phase 0 (Complete)

- CLI entry points aligned in `pyproject.toml`
- Main locustfile and taskset wiring functional
- Shared config and scenario registry in place

### Phase 1 (Complete)

- MinIO client utilities implemented
- Publish/list/cleanup by `run_id`
- Harness lifecycle implemented

### Phase 2 (In Progress)

Completed:

- Auth mode support (`none`, `auth0`, `local`)
- Scenario support including `spike` and `seed-only`
- Skip-seed/skip-teardown and custom run ID flags
- Documentation cleanup aligned to implementation

Remaining:

- Stronger threshold gate enforcement per service
- Warmup handling improvements
- Higher-throughput payload pooling/optimization

### Phase 3 (Not Started)

- Prometheus/Grafana in-repo provisioning/wiring
- Dashboard-driven report integration

### Phase 4 (Not Started)

- In-repo GitHub workflow automation
- Automated report publishing and notifications

---

## 15. Implementation Status

Current state: phases 0-1 complete, phase 2 active, phase 3-4 pending.

Last updated: 2026-02-03
