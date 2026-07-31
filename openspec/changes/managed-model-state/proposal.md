## Why

`DateTimeField(auto_now=True)` currently behaves only as a construction default and does not change on updates. Session also lacks a way to discard local changes and reload one instance, forcing callers to issue lower-level queries that are defeated by the identity map.

## What Changes

- Apply `auto_now` timestamps on every insert and update.
- Apply `auto_now_add` timestamps on insert only.
- Add `Session.refresh(instance)` to reload database values into the same Python object.
- Parse ISO-formatted database datetime values during model hydration.
- Preserve validation, identity-map identity, relation caching, unit-of-work, and cross-dialect execution invariants.
- Non-goals: partial-column refresh, server-generated defaults, timezone policy configuration, optimistic locking, and automatic refresh after every write.

## Capabilities

### New Capabilities

- `managed-model-state`: Managed timestamp persistence and explicit instance refresh.

### Modified Capabilities

None.

## Impact

DateTimeField conversion, Session persistence/materialization, tests, public documentation, and changelog change. No dependency or schema changes are required.
