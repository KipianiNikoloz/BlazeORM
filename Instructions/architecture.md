# Architecture

## Layered Flow
- Models/Fields/Relations → metadata drives query compilation and schema generation.
- Query layer (`Q`, compiler, `QuerySet`) builds SQL with dialect-aware quoting/placeholders; `select_related` produces joins, `prefetch_related` schedules follow-up fetches.
- Session orchestrates execution: binds a ContextVar for implicit usage, enforces identity map, caching, hooks, and performance tracking.
- Adapters execute SQL (execute/executemany/begin/commit/rollback/last_insert_id) and validate placeholders; Dialects render quoting, limit/offset, placeholders, capabilities.
- Schema builder + migration engine generate/apply DDL using dialects/adapters; destructive operations require explicit confirmation.

## Invariants
- All SQL must flow through an adapter; never bypass adapters/dialects for raw connections.
- Sessions own identity map and cache; `_materialize` must reuse existing instances when PK matches.
- Transactions must be initiated through `Session`/`TransactionManager`; nested transactions rely on dialect savepoint support.
- Eager loading must respect relationship metadata: `select_related` only for FK/O2O; `prefetch_related` for FK/reverse/m2m (including nested paths).
- Parameter placeholders must match the active dialect (SQLite `?`, Postgres/MySQL `%s`).

## Session & Identity Map Assumptions
- A single `Session` instance is assumed per logical unit of work; contextvar (`Session.current()`) enables implicit binding for managers and m2m managers.
- Identity map ensures one in-memory instance per model+PK; caching stores serialized dicts for PK lookups.
- M2M helpers mutate join tables and invalidate related caches on both sides.

## Eager Loading Mechanics
- `select_related`: compiler emits joins with aliased columns; hydration assigns related instances directly.
- `prefetch_related`: executes separate queries for specified relations; reverse and m2m paths are supported, including nested (`parent__child`). Related objects are bucketed by FK/through table values and cached on instances.

## Warnings / Risks
- Thread safety: session, identity map, and caches are not designed for concurrent multi-threaded access.
- ContextVar reliance: m2m managers and managers require an active session in the context; using them without `with session:` raises runtime errors.
- Cache consistency: caches are invalidated on delete/m2m mutations; bypassing session operations can leave stale caches.
- Placeholder correctness: cross-dialect SQL must honor dialect placeholders; hard-coded `?` outside SQLite is incorrect (see `current_state.md`).
