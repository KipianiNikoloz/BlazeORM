## Why

Creating a collection currently requires repetitive add/commit orchestration and makes atomic error handling easy to get wrong. A Session-level bulk API can provide one portable correctness boundary while preserving existing lifecycle behavior.

## What Changes

- Add `Session.bulk_create(instances)` returning the same instances in input order.
- Accept homogeneous, concrete, new model instances and reject duplicates or already-persisted objects.
- Persist the collection atomically, assign generated primary keys, and reuse normal validation, hooks, timestamps, identity-map, and cache behavior.
- Restore input object state when any insert fails.
- Return an empty list without opening a transaction for empty input.
- Non-goals: backend-specific multi-row SQL, conflict handling, batch sizing, relationship graph insertion, and asynchronous behavior.

## Capabilities

### New Capabilities

- `session-bulk-create`: Atomic multi-instance creation through Session.

### Modified Capabilities

None.

## Impact

Session persistence gains an additive method; persistence tests, documentation, and changelog change. SQL continues through existing dialect and adapter paths.
