## Why

Updating or deleting many matching rows currently requires raw SQL or per-instance hydration. Raw SQL bypasses model metadata and cache management, while per-instance work is unnecessarily expensive.

## What Changes

- Add filtered QuerySet `update(**values)` and `delete()` terminals returning affected-row counts.
- Require a non-empty WHERE expression and reject slicing, ordering, and eager-loading state.
- Validate update fields and disallow primary-key mutation.
- Execute through Session and dialect boundaries, clear stale identity/cache state, and honor Session autocommit.
- Document that per-instance validation, managed timestamps, and hooks are intentionally bypassed.
- Non-goals: joins, expressions, returning rows, cascades beyond database constraints, and unfiltered mutation.

## Capabilities

### New Capabilities

- `safe-bulk-mutations`: Guarded set-based update and delete operations.

### Modified Capabilities

None.

## Impact

The query compiler, QuerySet API, persistence cache behavior, tests, documentation, and changelog change. No schema or dependency changes occur.
