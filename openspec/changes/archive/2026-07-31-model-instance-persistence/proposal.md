## Why

BlazeORM exposes `Model.save()` and `Model.delete()` but both are placeholders. Users must understand the unit-of-work internals for basic persistence, which makes the public model API misleading and cumbersome.

## What Changes

- Make `Model.save()` insert new instances and update materialized or previously inserted instances.
- Make `Model.delete()` delete persisted instances.
- Resolve an explicitly supplied Session first and otherwise use the current context-bound Session.
- Give dirty registration the same autocommit behavior as add and delete.
- Preserve validation, hooks, identity-map, cache, and transaction behavior by routing through Session.
- This is additive for usable behavior; calls that previously raised `NotImplementedError` now persist.
- Non-goals: detached-instance merging, bulk persistence, asynchronous APIs, and database existence probes before save.

## Capabilities

### New Capabilities

- `model-instance-persistence`: Instance-level save and delete operations backed by Session.

### Modified Capabilities

None.

## Impact

The model base class, Session state tracking, persistence tests, public documentation, and changelog change. No schema or dependency changes are introduced.
