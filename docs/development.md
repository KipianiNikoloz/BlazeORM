# Development Guide

## Setup

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Use the virtual environment's Python for every command. Optional integration drivers are installed with `.[postgres]` and `.[mysql]` or explicitly in CI.

## Quality Gates

```bash
python -m ruff check .
python -m black --check .
python -m isort --check-only .
python -m mypy src
python -m pytest
python -m build
python -m twine check dist/*
```

For local database integrations:

```bash
docker compose -f docker-compose.integration.yml up -d
python -m pytest tests/integration
docker compose -f docker-compose.integration.yml down
```

Set `BLAZE_POSTGRES_DSN` and `BLAZE_MYSQL_DSN` to the values documented in `README.md`. Report unavailable integration infrastructure rather than silently claiming coverage.

## Change Workflow

1. Read `AGENTS.md`, the architecture, this guide, and the relevant reference section.
2. Inspect code and tests; current tested behavior is the baseline.
3. For a major change, create an OpenSpec change and complete proposal, specification, design, and tasks before implementation.
4. Work test-first: add one focused failing test, confirm the failure, implement the smallest behavior, and rerun focused tests.
5. Run the complete quality gates before integration.
6. Update public documentation and `CHANGELOG.md`, validate OpenSpec, synchronize specifications, and archive completed changes.

A major change modifies a public API, documented behavior, model/schema semantics, persistence semantics, SQL generation, or multiple subsystems. Documentation-only changes, internal behavior-preserving refactors, and isolated fixes with an unambiguous expected result do not require a new change proposal.

## Coding Rules

- Target Python 3.9+ and keep code typed. Do not add broad type ignores or relax quality configuration.
- Prefer small, focused units and explicit errors over silent fallbacks.
- Keep QuerySets immutable-style by cloning state rather than mutating an existing query.
- Use adapters/dialects for SQL and validate all supported backends when shared compilation changes.
- Preserve structured logging, redaction, hook order, transaction behavior, identity-map reuse, and cache invalidation.
- Add focused tests in the mirrored `tests/` subsystem. Relationship changes cover forward, reverse, and many-to-many behavior where applicable.
- Use conventional commit prefixes such as `feat:`, `fix:`, `docs:`, `test:`, and `chore:`. Each commit must be independently understandable and green.

## Documentation Matrix

| Change | Required documentation |
| --- | --- |
| Public API, behavior, or example | `README.md`, `docs/reference.md`, `CHANGELOG.md` |
| Architecture or invariant | `docs/architecture.md` |
| Tooling or contributor workflow | `docs/development.md`, and `AGENTS.md` if routing changes |
| Major capability | OpenSpec proposal/spec/design/tasks, then synchronized specification/archive |
| Release preparation | `src/blazeorm/version.py`, `CHANGELOG.md`, package metadata if needed |

Do not commit environments, caches, build artifacts, secrets, or Superpowers plan/spec files.
