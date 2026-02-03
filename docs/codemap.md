# Code Map

## Repository Purpose

Locust-based local load and end-to-end validation harness across platform services.

## Key Paths

- `src/`: Locust users, task sets, auth helpers, and metrics utilities.
- `scripts/`: Command entry points and report generation utilities.
- `tests/`: Unit and integration tests for the load-testing harness.
- `grafana/`: Dashboards for local observability during load runs.
- `docs/`: Curated onboarding and operational documentation.

## Local Commands

- `uv sync`
- `uv run lt-rule-engine --headless --scenario smoke`
- `uv run lt-trans-mgmt --headless --scenario smoke`
- `uv run lt-web`

## Local Test Commands

- `uv run lt-rule-engine --headless --scenario smoke`
- `uv run lt-trans-mgmt --headless --scenario smoke`

## API Note

This repository does not expose a business API. It drives traffic against other service APIs.

## Platform Integration

- Standalone mode: run this repository using its own local commands and Doppler project config.
- Consolidated mode: run this repository through `card-fraud-platform` compose stack for cross-service validation.
