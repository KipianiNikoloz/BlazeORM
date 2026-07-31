## Why

BlazeORM exposes `Meta.abstract` but concrete subclasses do not inherit abstract fields, leaving a documented model feature incomplete. Safe inheritance reduces repeated model declarations without sharing mutable field metadata between classes.

## What Changes

- Inherit cloned scalar and relationship fields from abstract model bases.
- Preserve declaration order, defaults, validators, relationship metadata, and automatic primary-key behavior.
- Allow explicit subclass field overrides and reject unresolved conflicts from multiple abstract bases.
- Keep concrete model inheritance unsupported; there are no breaking changes to existing models.
- Non-goals: multi-table inheritance, polymorphic queries, proxy models, and inherited Meta table/schema options.

## Capabilities

### New Capabilities

- `abstract-model-inheritance`: Deterministic field and relationship inheritance from abstract model bases.

### Modified Capabilities

None.

## Impact

Model metaclass construction, field/relation cloning, metadata and schema tests, public documentation, and changelog change. Persistence and database schemas change only when users opt into inherited fields.
