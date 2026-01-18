# Plan (Execute in Order)
Keep this plan updated after each completed step. Each step must include goal, likely files, tests, and required state updates.

1) Fix cross-dialect `Session.get` placeholders
- Goal: make `Session.get` use dialect-aware placeholders and add coverage for Postgres/MySQL.
- Files: `src/blazeorm/persistence/session.py`, `tests/persistence/` (new tests), possibly `tests/integration/` for adapters.
- Tests: relevant pytest (unit), plus integration when DSNs/drivers available.
- Update: mark issue resolved in `current_state.md`/`known_gaps.md`; adjust maturity if stabilized.
- Status: completed. `Session.get` uses dialect placeholders and unit tests cover Postgres/MySQL placeholder usage.

2) Reduce mypy ignores and tighten typing surface
- Goal: remove broad `# mypy: ignore-errors` where feasible, fix types, and adjust mypy config toward stricter checks without breaking CI.
- Files: core/query/persistence modules with ignores; `pyproject.toml` if config changes.
- Tests: mypy run; targeted pytest to ensure no regressions.
- Update: record typing status change in `current_state.md`; log remaining gaps in `known_gaps.md`.
- Status: completed. File-level `# mypy: ignore-errors` directives removed from `src/`; core/query/persistence/validation/schema typing fixes applied; warning flags enabled in mypy config; mypy/ruff/black/isort clean per local runs; further strictness still pending.

3) Adapter option coverage and error taxonomy
- Goal: extend `ConnectionConfig` and adapters for SSL/timeout/options parity; introduce consistent adapter-level exceptions.
- Files: `src/blazeorm/adapters/base.py`, adapter implementations, related tests under `tests/adapters/`, docs in Instructions/README and relevant files.
- Tests: unit adapter tests; integration when DSNs/drivers available.
- Update: reflect new capabilities in `current_state.md`; add/remove gaps accordingly.
- Status: completed. ConnectionConfig now parses DSN query options (autocommit/timeout/isolation/connect_timeout/SSL); adapters apply SSL/timeout options and raise Adapter* exceptions; tests added in `tests/adapters/`.

4) Schema builder enhancements (FKs/indexes) and migration safety
- Goal: emit FK/index metadata where appropriate and document destructive confirmation; ensure migrations remain explicit.
- Files: `src/blazeorm/schema/builder.py`, `schema` tests, README updates if needed.
- Tests: `tests/schema/*`, additional cases for FK/index rendering.
- Update: document new coverage and residual limitations in `current_state.md`/`known_gaps.md`.
- Status: completed. SchemaBuilder now emits FK constraints (including m2m join tables) and create/drop index SQL with warnings; schema tests updated and docs refreshed; migration version inserts use dialect placeholders.

5) Performance/observability exports and slow-query configuration
- Goal: add export/reset hooks for `PerformanceTracker` and configurable slow-query thresholds per env/session/adapter.
- Files: `src/blazeorm/utils/performance.py`, `session` integration, docs/tests under `tests/performance/`.
- Tests: performance unit tests; session regression tests.
- Update: note new features and any remaining observability gaps in `current_state.md`.
- Status: completed. Added export/reset hooks for performance stats, session-level export/reset helpers, and configurable slow-query thresholds via `BLAZE_SLOW_QUERY_MS` or per adapter/session; tests and docs updated.

6) Package distribution and PyPI release pipeline
- Goal: enable installing BlazeORM from PyPI with a reliable publish workflow (tagged releases).
- Files: `.github/workflows/` (publish workflow), `pyproject.toml` (package metadata/versioning), `README.md`/`src/blazeorm/README.md` (install docs), possibly `CHANGELOG.md`.
- Tests: build package, run CI, optional `twine check`/`pip install` smoke tests.
- Update: reflect release pipeline status and install guidance in `current_state.md`/`known_gaps.md`.
