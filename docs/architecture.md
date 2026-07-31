# Architecture

BlazeORM is a synchronous, inspectable ORM for SQLite, PostgreSQL, and MySQL. It targets Python developers who want declarative models, explicit persistence, eager loading, migrations, caching, hooks, and query observability without a framework-sized runtime.

## Boundaries

BlazeORM does not provide asynchronous APIs, automatic schema diffs, implicit migrations, an admin UI, or direct driver access outside adapters.

## Layered Flow

1. Models, fields, and relationships provide metadata.
2. Query objects and the SQL compiler translate metadata and expressions into dialect-aware SQL.
3. A session executes queries and coordinates validation, the unit of work, identity map, cache, hooks, and performance tracking.
4. Adapters own DB-API connections and execution; dialects own quoting, placeholders, limits, and capability flags.
5. The schema builder and migration engine produce and apply explicit DDL with destructive-operation safeguards.

## Non-Negotiable Invariants

- All SQL execution flows through an adapter. Shared SQL uses dialect quoting and placeholders; never hard-code SQLite syntax.
- QuerySet iteration and relationship managers require an explicit or context-bound session.
- Sessions own their identity maps and caches. Materialization must reuse an existing model instance for the same model and primary key.
- Persistence runs `full_clean()` before saving and invalidates affected caches after writes and relationship mutations.
- Transactions use `TransactionManager`; nested transactions depend on dialect savepoint support.
- Migrations are explicit. Operations marked destructive require `force=True`.
- DSNs and sensitive parameters are redacted in logs. Configuration comes from `ConnectionConfig.from_dsn()` or `from_env()`.
- Public behavior remains compatible unless an approved OpenSpec change says otherwise.

## Relationship and Loading Semantics

- Foreign keys and one-to-one fields store remote keys and may cache hydrated related objects.
- Many-to-many fields use explicit through tables and invalidate both sides of the relation cache after mutation.
- `select_related()` is join-based and applies to foreign-key/one-to-one paths.
- `prefetch_related()` performs follow-up bulk queries for forward, reverse, many-to-many, and nested paths.

## Operational Assumptions

- Use one `Session` per logical unit of work and preferably per thread. Internal state uses locks, but a session is not a general shared concurrency primitive.
- Context variables make manager usage convenient inside `with session:`; code outside a bound context must pass a session explicitly.
- The in-memory cache is process-local. Writes that bypass the session can make it stale.

## Terminology

- **Adapter:** DB-API wrapper for connection, execution, transactions, parameter validation, and logging.
- **Dialect:** Backend-specific SQL rendering and capability flags.
- **Session:** Unit-of-work coordinator and execution boundary.
- **Identity map:** Per-session mapping that ensures one in-memory instance per model and primary key.
- **QuerySet:** Immutable-style chainable query definition evaluated through a session.
- **SchemaBuilder:** DDL generator driven by model metadata.
- **MigrationEngine:** Explicit ordered migration runner with version tracking.
- **PerformanceTracker:** SQL timing and repeated-query/N+1 observer.
