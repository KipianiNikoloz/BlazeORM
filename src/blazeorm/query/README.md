Query Builder, Compiler, and Execution
======================================

What Lives Here
---------------
- `expressions.py`: `Q` objects with AND/OR/NOT composition for filters.
- `compiler.py`: SQL compiler translating `QuerySet` state into SQL + params (supports joins for `select_related`, ordering, limit/offset).
- `queryset.py`: Chainable `QuerySet`, session-bound iteration, `select_related`/`prefetch_related`, nested prefetch (including m2m), and default `QueryManager`.
 
Key Behaviors
-------------
- `QuerySet.to_sql()` uses the dialect to render quoting and limit/offset, and raises when `select_related` hits unsupported m2m paths.
- Iteration:
  - Must be bound to a `Session` (explicit via `Session.query()` or implicit via current context).
  - Materializes rows using the session identity map and caches.
  - Hydrates `select_related` via joins and `prefetch_related` via separate bulk queries (forward, reverse, m2m, nested paths).
- Managers:
  - `QueryManager` is auto-attached to models; respects context-bound session when used inside `with session:`.

Usage Notes
-----------
- Use `select_related("fk")` for join-based eager loading; use `prefetch_related("reverse", "m2m", "nested__path")` for bulk fetches across relationships.
- For m2m, prefetch handles both forward and reverse related names; nested prefetch cascades to related collections.
- Query compilation assumes `Q` objects produce safe SQL fragments; parameter counts are validated by adapters.

Testing References
------------------
- `tests/query/test_queryset.py`, `tests/query/test_queryset_execution.py`, `tests/performance/test_n_plus_one.py`.

