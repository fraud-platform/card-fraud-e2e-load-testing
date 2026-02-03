# Code Map

## Repository Purpose

Locust-based local load and end-to-end validation harness across services.

## Primary Areas

- `app/` or `src/`: service or application implementation.
- `tests/` or `e2e/`: automated validation.
- `scripts/` or `cli/`: local developer tooling.
- `docs/`: curated documentation index and section guides.

## Local Commands

- `uv sync`
- `uv run lt-web`
- `uv run lt-trans-mgmt --headless --scenario smoke`

## Test Commands

- `uv run lt-rule-engine --headless --scenario smoke`
- `uv run lt-trans-mgmt --headless --scenario smoke`

## API Note

No standalone business API; this repo drives traffic against other service APIs.

## Deployment Note

Local execution only in current phase; CI load pipelines are deferred.
