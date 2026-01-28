Session, Unit of Work, Identity Map, Transactions
=================================================

What Lives Here
---------------
- `session.py`: Session orchestration (connections, execute, query binding, identity map, caching, hooks, performance tracker, m2m helpers).
- `unit_of_work.py`: Tracks new/dirty/deleted instances for flush/commit.
- `identity_map.py`: Stores live instances keyed by model + PK.
- `transaction.py`: Transaction manager supporting nested transactions/savepoints (adapter-aware).
- `migration.py` (engine reference): Applied via `schema` but uses adapters/dialect.

Key Behaviors
-------------
- Session lifecycle:
  - `Session(adapter, connection_config|dsn, autocommit=False, cache_backend, performance_threshold, slow_query_ms)` initializes adapter, slow-query threshold, and performance tracker.
  - Context-managed (`with session:`) binds a ContextVar for implicit query execution.
  - `begin/commit/rollback` wrap the adapter transaction manager; autocommit triggers immediate commit after `add/delete` when enabled.
- Execution:
  - `execute` wraps adapter calls with timing, logging, redaction, and performance tracking; uses adapter param validation.
  - `query(Model)` returns a session-bound `QuerySet`.
- Materialization:
  - Identity map reuse, 2nd-level cache usage, `_normalize_db_value` coercion for related instances, `_row_to_dict` mapping.
- M2M helpers:
  - `add_m2m/remove_m2m/clear_m2m` plus `Model.m2m_*` sugar manage join rows and invalidate relation caches (forward/reverse).
- Hooks:
  - Fires `before/after_validate/save/delete/commit` around persistence operations.

Usage Notes
-----------
- Always bind operations to a session; manager iteration inside `with session:` reuses the same connection/identity map.
- DSN/ConnectionConfig supports autocommit, isolation level, timeouts; adapters enforce transaction semantics.
- Slow-query logging threshold defaults to 200ms or `BLAZE_SLOW_QUERY_MS`; override per session with `slow_query_ms`.
- Performance stats available via `Session.query_stats()`, `Session.export_query_stats(reset=..., include_samples=...)`, and `Session.reset_query_stats()`.
- Session, identity map, and cache operations are guarded by locks for basic thread safety, but prefer a dedicated Session per thread.

Testing References
------------------
- `tests/persistence/test_session.py`, `tests/persistence/test_many_to_many.py`, `tests/query/test_queryset_execution.py`, `tests/performance/test_n_plus_one.py`.
