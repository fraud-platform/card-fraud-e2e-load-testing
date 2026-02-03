# Card Fraud E2E Load Testing Docs

Locust-based local load and end-to-end validation harness across services.

## Documentation Standard

- File names: lowercase kebab-case (for example `local-setup.md`).
- Section folders: numbered lowercase (`01-setup` through `07-reference`).
- Keep docs concise and executable for local development.
- Do not publish TODO/archive/session notes.

## Section Map

- `01-setup/`: prerequisites, bootstrap, local environment setup.
- `02-development/`: daily development workflow and conventions.
- `03-api/`: API surface and contract references.
- `04-testing/`: local test strategy and commands.
- `05-deployment/`: local deployment approach and release notes.
- `06-operations/`: runbooks, troubleshooting, observability.
- `07-reference/`: glossary, decisions, and cross-repo references.

## Quick Start Commands

- `uv sync`
- `uv run lt-web`
- `uv run lt-trans-mgmt --headless --scenario smoke`

## Published Files

- `docs/README.md`
- `docs/codemap.md`
