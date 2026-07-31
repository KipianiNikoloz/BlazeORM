# BlazeORM Agent Guide

This file is the entry point for automated contributors. Keep it short and use the linked documents as the durable source of project context.

## Read Before Changing Code

1. Read `README.md` for the supported public surface.
2. Read `docs/architecture.md` for scope and non-negotiable invariants.
3. Read `docs/development.md` for setup, quality gates, and workflow.
4. Read `docs/reference.md` for the subsystem being changed.
5. If the change is major, read its artifacts under `openspec/changes/` before editing.

Code and tests describe current behavior. OpenSpec artifacts describe an approved behavior change. Documentation must agree with both when work is complete.

## Repository Map

- `src/blazeorm/`: library code, split by core, query, persistence, adapters, dialects, schema, security, cache, hooks, validation, and utilities.
- `tests/`: unit and integration coverage mirroring the library subsystems.
- `examples/`: executable blog and library examples.
- `docs/`: architecture, development workflow, and consolidated reference documentation.
- `openspec/`: specifications and major change artifacts.

## Required Workflow

- Treat a change as **major** when it changes a public API, documented behavior, model/schema semantics, persistence behavior, SQL generation, or more than one subsystem. Start it with OpenSpec, validate the artifacts, implement its tasks, then sync/archive the change.
- Documentation-only edits, internal refactors with no behavior change, and isolated bug fixes with an obvious expected result may proceed without a new OpenSpec change.
- Use test-driven development for behavior changes: add a focused failing test, confirm the expected failure, implement, then run the focused and full suites.
- Keep SQLite, PostgreSQL, and MySQL behavior aligned. SQL must use adapters and dialect-provided quoting/placeholders.
- Preserve backward compatibility unless the OpenSpec change explicitly authorizes a break.
- Never weaken tests, typing, linting, redaction, migration safety, or transaction safeguards to make a check pass.

## Documentation Updates

- Public APIs or examples: update `README.md` and `docs/reference.md`.
- Architecture, constraints, or subsystem boundaries: update `docs/architecture.md`.
- Contributor commands or workflow: update `docs/development.md` and this file when its routing changes.
- User-visible behavior: add an entry to `CHANGELOG.md`.
- Major changes: keep OpenSpec tasks/specifications synchronized and archive the completed change.

## Completion Gate

Run the commands in `docs/development.md`. Report skipped integration tests explicitly. Do not commit caches, build outputs, virtual environments, secrets, or Superpowers planning files.
