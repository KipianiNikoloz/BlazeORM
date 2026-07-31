## Context

Session already owns validation, hooks, unit-of-work registration, SQL generation, identity-map updates, cache updates, and transaction boundaries. Model needs only enough lifecycle state to choose new versus dirty registration without guessing from primary-key presence, because new instances may use application-assigned primary keys.

## Goals / Non-Goals

**Goals:**
- Provide convenient instance persistence without bypassing Session invariants.
- Correctly distinguish new instances from materialized or inserted instances.
- Make explicit and context-bound use behave identically on SQLite, PostgreSQL, and MySQL.

**Non-Goals:**
- Detached graph merging, optimistic locking, upserts, bulk operations, or probing the database to infer lifecycle state.

## Decisions

1. Model stores a private `_persisted` boolean initialized to false. Session sets it true after materialization, cache hydration, or a successful insert. This supports application-assigned primary keys without mistaking them for existing rows.
2. `save(session=None)` and `delete(session=None)` resolve the explicit Session first, then `Session.current()`. Missing sessions raise a descriptive `RuntimeError`.
3. `save()` delegates to `Session.add()` when new and `Session.mark_dirty()` when persisted. `delete()` rejects new instances with `ValueError` and otherwise delegates to `Session.delete()`.
4. `Session.mark_dirty()` commits when Session autocommit is enabled, matching add and delete. All SQL remains dialect-generated and adapter-executed through existing persistence helpers.
5. A successful delete sets `_persisted` false after hooks and cache invalidation. Re-saving that object is therefore an explicit new insert rather than a silent update of a missing row.

## Risks / Trade-offs

- Lifecycle state is local rather than database-probed -> avoids extra queries and preserves assigned-key inserts, but manually constructed representations of existing rows remain new until loaded through Session.
- Delete followed by save attempts an insert -> explicit and predictable, though callers remain responsible for primary-key conflicts.
- A failed flush leaves state unchanged because flags change only after successful SQL execution.

## Migration Plan

The methods were previously unusable placeholders. Reverting the model methods and lifecycle assignments restores prior behavior without data migration.

## Open Questions

None.
