# Code Map

## Core Layout

- `src/locustfile.py`: Locust user classes and task loading.
- `src/tasksets/`: per-service task definitions.
  - `rule_engine/`
  - `rule_management/`
  - `transaction_mgmt/`
- `src/generators/`: synthetic payload/test data generators.
- `src/utilities/`: harness, reporting, metrics, object-store helpers.
- `scripts/`: CLI entry points (`lt-run`, `lt-rule-engine`, etc.).
- `tests/`: unit/integration checks for load test code.

## Key Commands

- `uv run lt-web`
- `uv run lt-rule-engine --headless --scenario smoke`
- `uv run lt-rule-mgmt --headless --scenario smoke`
- `uv run lt-trans-mgmt --headless --scenario smoke`

## Integration Role

Provides local-first e2e/load validation for the full platform stack.
