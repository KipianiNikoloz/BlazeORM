## Why

BlazeORM users must materialize entire QuerySets or drop to `Session.get()` for common single-result and aggregate questions. Terminal operations make queries ergonomic while avoiding unnecessary model hydration.

## What Changes

- Add `first()`, `get()`, `count()`, and `exists()` to QuerySet and QueryManager.
- Add public query cardinality exceptions for zero and multiple `get()` results.
- Generate efficient cross-dialect count and existence SQL that respects filters and slicing without eager-loading joins.
- Share bound-session resolution between iteration and terminal methods.
- Preserve `Session.get()` and all existing QuerySet behavior; there are no breaking changes.
- Non-goals: bulk update/delete, result caching, async evaluation, and changing Session APIs.

## Capabilities

### New Capabilities

- `queryset-terminal-operations`: Evaluation methods, cardinality errors, and aggregate/probe semantics for QuerySets and managers.

### Modified Capabilities

None.

## Impact

The SQL compiler, QuerySet/QueryManager, query exports, package exports, query tests, public documentation, and changelog change. No external dependencies or schema changes are introduced.
