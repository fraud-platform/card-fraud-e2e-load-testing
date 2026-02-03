# AGENTS.md

This is the canonical instruction file for AI coding agents in this repository.

Applies to all assistants (Codex, Claude, ChatGPT, Cursor, Copilot, and similar tools).

## Cross-Repo Agent Standards

- Secrets: Doppler-only workflows. Do not create or commit `.env` files.
- Commands: use repository wrappers from `pyproject.toml` or `package.json`; avoid ad-hoc commands.
- Git hooks: run `git config core.hooksPath .githooks` after clone to enable pre-push guards.
- Docs publishing: keep only curated docs in `docs/01-setup` through `docs/07-reference`, plus `docs/README.md` and `docs/codemap.md`.
- Docs naming: use lowercase kebab-case for docs files. Exceptions: `README.md`, `codemap.md`, and generated contract files.
- Never commit docs/planning artifacts named `todo`, `status`, `archive`, or session notes.
- If behavior, routes, scripts, ports, or setup steps change, update `README.md`, `AGENTS.md`, `docs/README.md`, and `docs/codemap.md` in the same change.
- Keep health endpoint references consistent with current service contracts (for APIs, prefer `/api/v1/health`).
- Preserve shared local port conventions from `card-fraud-platform` unless an explicit migration is planned.
- Before handoff, run the repo's local lint/type/test gate and report the exact command + result.

## 1) Mission

Maintain and improve this repository as a **local-first E2E/load testing suite** for the card fraud platform.

Primary SUT priorities:

1. `card-fraud-rule-engine` (Quarkus/Java) - highest throughput and latency sensitivity
2. `card-fraud-transaction-management` (FastAPI/Python) - medium load and correctness
3. `card-fraud-rule-management` (FastAPI/Python) - low throughput governance APIs

## 2) Mandatory Safety Rules

Never:

1. Modify production services from this repo
2. Commit secrets, tokens, or real credentials
3. Run load tests against production without explicit approval
4. Ignore failing tests or broken checks
5. Use real card numbers or real PII in generated fixtures

Always:

1. Use environment variables for URLs and credentials
2. Mask sensitive values in logs and docs
3. Keep seed/test/teardown behavior idempotent
4. Keep docs in sync with implementation
5. Preserve synthetic-only test data guarantees

## 3) Agent Workflow Contract

For any non-trivial change:

1. Read docs + implementation before editing
2. Validate commands/paths against code (`pyproject.toml`, `scripts/`, `src/`)
3. Update docs and code together when behavior changes
4. Record known gaps as "not implemented yet" instead of documenting aspirational behavior as complete

Definition of done for docs changes:

- No stale commands
- No stale paths
- Environment variable tables match current code
- Roadmap/future sections are clearly marked as planned

## 4) Quick Start (Agent Friendly)

```bash
# Install deps
uv sync --extra load-test

# Smoke test
uv run lt-rule-engine --users=50 --spawn-rate=10 --run-time=2m --scenario smoke --auth-mode none

# Generate sample synthetic data
uv run gen-transactions --count=1000
uv run gen-users --count=1000
uv run gen-rules --count=100
```

## 5) Canonical Commands

### Load testing

| Command | Purpose | Example |
|---|---|---|
| `uv run lt-run` | Main runner (all or specific service) | `uv run lt-run --service all --scenario baseline --auth-mode none` |
| `uv run lt-web` | Locust web UI | `uv run lt-web` |
| `uv run lt-rule-engine` | Rule Engine wrapper | `uv run lt-rule-engine --users=1000 --run-time=10m` |
| `uv run lt-trans-mgmt` | Transaction Mgmt wrapper | `uv run lt-trans-mgmt --users=200 --run-time=10m` |
| `uv run lt-rule-mgmt` | Rule Mgmt wrapper | `uv run lt-rule-mgmt --users=50 --run-time=10m` |

### Data generation

| Command | Purpose |
|---|---|
| `uv run gen-transactions` | Generate synthetic transactions |
| `uv run gen-users` | Generate synthetic users |
| `uv run gen-rules` | Generate synthetic rules |
| `uv run gen-rulesets` | Generate synthetic rulesets |

### Reporting

| Command | Purpose |
|---|---|
| `uv run gen-report` | Build combined HTML/Markdown summary from run summary files |

## 6) Service Notes and Performance Intent

### Rule Engine (HIGH load)

- Target intent: P50 < 5ms, P95 < 15ms, P99 < 30ms, high RPS workload
- Tasksets: `src/tasksets/rule_engine/`
- Config source: `src/config/defaults.py` (`RuleEngineConfig`)
- Typical scenario focus: `smoke`, `baseline`, `stress`, `soak`, `spike`

### Transaction Management (MEDIUM load)

- Local target intent: moderate throughput (commonly ~50 TPS in local runs)
- Tasksets: `src/tasksets/transaction_mgmt/`
- Config source: `src/config/defaults.py` (`TransactionManagementConfig`)

### Rule Management (LOW load)

- Governance-focused API, low throughput
- Tasksets: `src/tasksets/rule_management/`
- Config source: `src/config/defaults.py` (`RuleManagementConfig`)

## 7) Source-of-Truth File Map

| Purpose | Path |
|---|---|
| Main Locust entry | `src/locustfile.py` |
| Runner CLI | `scripts/run_load_test.py` |
| Scenario + service config | `src/config/defaults.py` |
| Auth modes | `src/auth/auth0.py` |
| Seed/test/teardown harness | `src/utilities/harness.py` |
| MinIO/S3 utilities | `src/utilities/minio_client.py` |
| Report writer | `src/utilities/reporting.py` |
| Data generators | `scripts/generate_*.py` and `src/generators/__init__.py` |

## 8) Environment Variables

| Variable | Required | Description |
|---|---|---|
| `RULE_ENGINE_URL` | Yes (rule engine runs) | Rule Engine base URL (default `http://localhost:8081`) |
| `RULE_MGMT_URL` | Rule mgmt runs | Rule Management base URL (default `http://localhost:8000`) |
| `TRANSACTION_MGMT_URL` | Trans runs | Transaction Mgmt base URL (default `http://localhost:8002`) |
| `AUTH_MODE` | No | `none`, `auth0`, or `local` |
| `AUTH0_DOMAIN` | For `auth0` | Auth0 domain |
| `AUTH0_AUDIENCE` | For `auth0` | Auth0 API audience |
| `AUTH0_CLIENT_ID` | For `auth0` | Auth0 client ID |
| `AUTH0_CLIENT_SECRET` | For `auth0` | Auth0 client secret |
| `LOCAL_SIGNING_KEY` | For `local` | Optional local signing key |
| `S3_ENDPOINT_URL` | No | MinIO/S3 endpoint (default `http://localhost:9000`) |
| `S3_ACCESS_KEY_ID` | No | S3 access key (default `minioadmin`) |
| `S3_SECRET_ACCESS_KEY` | No | S3 secret key (default `minioadmin`) |
| `S3_BUCKET_NAME` | No | Artifact bucket (default `fraud-gov-artifacts`) |

Backward-compatible fallback variables still supported:

- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_SECURE`

## 9) Auth Behavior and Local JWT Bypass

`--auth-mode` values:

- `none`: no auth header
- `auth0`: Auth0 client credentials token flow
- `local`: locally signed token

For local-only API development/testing, services may allow JWT bypass:

```bash
APP_ENV=local
SECURITY_SKIP_JWT_VALIDATION=true
```

When bypass is enabled in target services, run load tests with `--auth-mode none`.

## 10) Scenarios

Supported scenarios in runner/config:

- `smoke`
- `baseline`
- `stress`
- `soak`
- `spike`
- `seed-only`

Seed/test/teardown defaults:

- Seed enabled
- Teardown enabled
- Run metadata written under `html-reports/`

Override flags:

- `--skip-seed`
- `--skip-teardown`
- `--run-id <id>`

## 11) Test Data Rules (Strict)

When generating fixtures:

1. Never use real card PAN data; masked/tokenized patterns only
2. Never use real PII or copied production data
3. Prefer UUIDs/random IDs for synthetic entities
4. Include edge-case coverage where useful (null/empty/extreme values)

Example synthetic transaction shape:

```json
{
  "transaction_id": "txn_abc123",
  "card_id": "411111******1111",
  "amount": 5000,
  "country": "IN"
}
```

## 12) Reporting Expectations

After meaningful load runs:

```bash
uv run gen-report
```

Expected outputs:

- `html-reports/locust/` (Locust HTML/CSV)
- `html-reports/run-summary-*.json` and `.csv`
- `html-reports/combined/` (combined HTML + markdown)

## 13) Known Status Boundaries

- CI workflows are not yet committed in this repo (local-first execution is current mode)
- Prometheus/Grafana containers exist in compose, but full local provisioning/config files are not yet complete

Document these as "planned"; do not describe them as fully operational.

## 14) Troubleshooting

| Issue | Suggested check |
|---|---|
| Auth failures | Verify `AUTH0_*` values and selected `--auth-mode` |
| Service unreachable | Confirm service container/process and URL/port |
| High latency or 429 | Reduce user count/spawn rate and re-run |
| MinIO issues | Verify `S3_*` or `MINIO_*` env vars and bucket permissions |
| Missing combined report rows | Ensure `run-summary-*.json` exists under `html-reports/` |

## 15) Documentation Hygiene Rules

When editing docs:

1. Keep command examples executable as written
2. Prefer current implementation details over aspirational descriptions
3. Keep roadmap/phase items, but clearly label as future/planned
4. Avoid duplicate conflicting command docs across files
5. Update `README.md`, `AGENTS.md`, and `docs/*.md` together when behavior changes
