## Why

Session rollback currently restores only unit-of-work membership. After a flush, Python objects can still look inserted, updated, or deleted even though the database reverted, and caches may contain uncommitted data.

## What Changes

- Snapshot scalar values, clean-state baselines, relation caches, lifecycle flags, and identity-map membership at each transaction/savepoint boundary.
- Restore model and cache state on rollback alongside unit-of-work sets.
- Lazily capture instances first registered after a transaction begins.
- Preserve nested savepoint semantics so inner rollback returns to inner entry state while outer rollback returns to outer entry state.
- Non-goals: arbitrary user attributes, external cache transactional guarantees, cross-Session coordination, and database isolation changes.

## Capabilities

### New Capabilities

- `transaction-state-rollback`: Transaction-consistent in-memory model and cache restoration.

### Modified Capabilities

None.

## Impact

Session transaction bookkeeping changes internally; persistence tests, architecture/reference docs, and changelog change. Public method signatures remain compatible.
