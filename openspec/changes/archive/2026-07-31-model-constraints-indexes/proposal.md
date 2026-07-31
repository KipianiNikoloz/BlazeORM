## Why

Field-level uniqueness and indexes cannot express multi-column business rules or access paths. Users must hand-write DDL and keep it disconnected from model metadata.

## What Changes

- Add public immutable `UniqueConstraint` and `Index` metadata objects.
- Accept `Meta.constraints` and `Meta.indexes` on models, including inheritance from abstract bases.
- Validate referenced scalar fields, duplicate fields, duplicate definitions, and explicit-name collisions during model construction.
- Render portable table-level unique constraints and composite index create/drop SQL.
- Prepare and lock the cumulative release as BlazeORM 0.4.0.
- Non-goals: check/exclusion/partial/expression constraints, index methods or included columns, runtime schema introspection, and automatic migrations.

## Capabilities

### New Capabilities

- `model-constraints-indexes`: Declarative multi-field uniqueness and indexes.

### Modified Capabilities

None.

## Impact

Core metadata, public exports, schema generation, tests, documentation, changelog, package version, and uv lock change. Migrations remain explicit.
