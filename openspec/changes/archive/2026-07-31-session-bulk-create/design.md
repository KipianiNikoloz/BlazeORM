## Context

`_persist_new` already owns validation, hooks, managed timestamps, SQL generation, generated-key retrieval, identity-map insertion, and caching. Reusing it avoids a second backend-specific persistence implementation.

## Goals / Non-Goals

**Goals:** ergonomic collection creation, atomicity, generated keys, lifecycle consistency, deterministic errors, and input order preservation.

**Non-Goals:** single-statement multi-row INSERT, conflict policies, relationships, streaming iterables, batch tuning, or heterogeneous models.

## Decisions

1. `bulk_create` materializes the iterable once and returns an empty list immediately for no instances.
2. It validates that every value is a concrete Model of exactly the same class, is not repeated by identity, and is not already persisted.
3. The method snapshots each object's scalar, initial, related-cache, and lifecycle state before writes. It runs all inserts inside `Session.transaction()` and restores object snapshots if any validation, hook, adapter, or commit error escapes.
4. Each instance uses `_persist_new` in input order. This is portable and guarantees generated primary keys and existing hook/timestamp/cache behavior; backend-specific multi-row optimization is deferred.
5. A top-level call commits atomically. Inside an existing transaction it uses the Session's nested savepoint behavior, leaving the outer transaction in control.

## Risks / Trade-offs

- One INSERT per object is slower than native multi-row syntax -> correctness is identical on all backends and leaves room for later adapter capability optimization.
- Top-level calls commit immediately -> makes the creation contract atomic and explicit; callers needing a larger unit use an outer Session transaction.

## Migration Plan

The method is additive and requires no schema or data migration.

## Open Questions

None.
