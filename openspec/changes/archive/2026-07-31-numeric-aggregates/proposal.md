## Why

BlazeORM can count rows but callers must fetch values or write SQL for basic numeric summaries. Database-side aggregates reduce data transfer and make reporting queries composable with existing filters and slices.

## What Changes

- Add `sum(field)`, `average(field)`, `minimum(field)`, and `maximum(field)` to QuerySet and QueryManager.
- Support integer, float, and automatic primary-key fields.
- Preserve filters and the exact ordered slice before aggregation.
- Return `None` for empty inputs and reject non-numeric or unknown fields before execution.
- Non-goals: grouped aggregates, annotations, expressions, decimal fields, and relationship traversal.

## Capabilities

### New Capabilities

- `numeric-aggregates`: Portable scalar numeric aggregate terminals.

### Modified Capabilities

None.

## Impact

The query compiler and public query API gain additive methods; tests, documentation, and changelog change. No schema or dependency changes occur.
