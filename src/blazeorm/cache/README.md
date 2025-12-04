Caching
=======

What Lives Here
---------------
- `base.py`: Cache backend protocol (get/set/delete).
- `memory.py`: In-memory cache implementation.

Key Behaviors
-------------
- Session-level 2nd-level cache uses configured backend to cache materialized instances by model + PK.
- Cache invalidation occurs on delete and m2m mutations; refresh on save.

Usage Notes
-----------
- Provide custom cache backend to `Session(cache_backend=...)` if needed.
- In-memory cache is best-effort and process-local; not distributed.

Testing References
------------------
- `tests/cache/test_cache.py`, `tests/persistence/test_session.py`.

