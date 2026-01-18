# Current State (Authoritative Snapshot)
Update this file whenever behavior, coverage, or plans change.

## Implemented Features (grounded in code/tests)
- Models/fields: typed fields (int/float/string/bool/datetime/auto PK), descriptors, defaults, validation (`full_clean`), dirty tracking.
- Relations: FK, OneToOne, ManyToMany with forward/reverse accessors; m2m managers support add/remove/clear and caching; relation registry auto-installs reverse accessors.
- Query layer: `Q` expressions, compiler, `QuerySet` with filter/exclude/order/limit/offset, `select_related` joins, `prefetch_related` for FK/reverse/m2m (including nested paths); session-bound iteration.
- Persistence: `Session` with adapter/dialect binding, identity map, unit-of-work, nested transactions/savepoints, contextvar-bound session, caching, hooks, m2m helpers, performance tracker (`query_stats`).
- Adapters/dialects: SQLite/Postgres/MySQL adapters with parameter validation, DSN redaction, structured logging, DSN-query option parsing (autocommit/timeout/isolation/connect_timeout/SSL), and Adapter* exception taxonomy; dialects handle quoting/limit/placeholders/capabilities.
- Schema/migrations: `SchemaBuilder` renders tables and m2m join tables with FK constraints plus index DDL helpers; `MigrationEngine` with version table, dialect placeholders, and destructive-operation confirmation.
- Security: DSN parsing/redaction (`ConnectionConfig.from_dsn/from_env`) including sensitive query params and parameter value masking, destructive migration confirmation.
- Caching: NoOp and in-memory backends with session 2nd-level cache.
- Hooks: before/after validate/save/delete, after_commit via dispatcher.
- Performance: query timing, N+1 detection with warnings, export/reset stats helpers, and configurable slow-query thresholds via env/session/adapter.
- Examples: blog and library apps exercising eager loading and m2m; tests assert demo flows.

## Maturity by Subsystem
- Core models/fields/relations: **stable** (well tested; m2m implemented and cached).
- Query compilation & eager loading: **stable** (select_related/prefetch including m2m) with cross-dialect SQL generation; relies on adapter placeholders.
- Session/unit-of-work/transactions: **stable** with thread-safety assumptions.
- Adapters/dialects: **stable** for basic usage; reconnect/autocommit handling present for Postgres/MySQL; integration tests are env/driver-gated.
- Schema/migrations: **stable** for table/join-table/index/foreign-key DDL with destructive-operation warnings; explicit migration operations remain required.
- Caching & hooks: **stable** within single-threaded session context.
- Performance tracker: **stable** warnings/stats with export/reset helpers and configurable slow-query thresholds.
- Docs/Instructions: **new layout**; keep synchronized with code and tests.

## Known Correctness/Behavior Issues (must be fixed before claiming production readiness)
- Instructions folder is gitignored in `.gitignore`; new files may be untracked unless explicitly added.

## Branch Reality
- `main` is outdated (last change: float datatype). Active work is on branches; current HEAD is `chore/mypy-alignment` with all features/tests.
- Assume HEAD reflects truth unless a branch states otherwise; do not base work from `main` without merging.

## CI / Tooling Reality
- CI (`.github/workflows/ci.yml`) runs ruff, black, isort, mypy, pytest. Integration tests depend on `BLAZE_POSTGRES_DSN`/`BLAZE_MYSQL_DSN` and drivers; otherwise they skip.
- No PyPI publish workflow exists yet; packaging is local-only until a release pipeline is added.
- `pyproject.toml` sets mypy `strict = false` and `ignore_missing_imports = false` with overrides for optional drivers (`psycopg`, `pymysql`, `MySQLdb`); file-level `# mypy: ignore-errors` directives have been removed and core/query/persistence/validation/schema typing fixes were applied. Warning flags (`warn_unused_ignores`, `warn_redundant_casts`, `warn_unreachable`, `warn_unused_configs`) are enabled, but typing remains lenient and needs further tightening.
- Local runs of mypy/ruff/black/isort are clean after typing/lint fixes and unused-ignore cleanup; CI status unchanged.

## Expectations for Future Updates
- When you change behavior or coverage, update this file: reflect new features, maturity shifts, fixed/new issues, CI/tooling changes, and branch status if relevant.
- Keep descriptions code-backed; cite file paths for issues where possible.
