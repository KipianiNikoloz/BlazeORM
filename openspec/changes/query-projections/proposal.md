## Why

Callers must currently hydrate complete model instances even when they need only a few scalar values. This wastes work and makes common reporting and serialization paths verbose.

## What Changes

- Add terminal `values(*fields)` and `values_list(*fields, flat=False)` methods to QuerySet and QueryManager.
- Select only requested base-model columns while preserving filters, ordering, limits, and offsets.
- Return dictionaries, tuples, or scalars without model hydration, eager loading, identity-map insertion, or cache writes.
- Reject missing/unknown fields and invalid `flat=True` shapes explicitly.
- Non-goals: relationship traversal, aliases, annotations, streaming cursors, and lazy projection QuerySets.

## Capabilities

### New Capabilities

- `query-projections`: Efficient terminal scalar-field projections.

### Modified Capabilities

None.

## Impact

The query compiler, QuerySet/QueryManager, query tests, documentation, and changelog change. SQL remains portable through dialect quoting and placeholders.
