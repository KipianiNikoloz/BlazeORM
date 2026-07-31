# safe-bulk-mutations Specification

## Purpose
TBD - created by archiving change safe-bulk-mutations. Update Purpose after archive.
## Requirements
### Requirement: Filtered bulk update
QuerySet SHALL expose `update(**values)` to update matching rows and return the adapter's affected-row count.

#### Scenario: Valid filtered update
- **WHEN** update receives scalar model fields on a filtered query
- **THEN** it executes one dialect-safe UPDATE and returns the number of affected rows

### Requirement: Filtered bulk delete
QuerySet SHALL expose `delete()` to delete matching rows and return the adapter's affected-row count.

#### Scenario: Valid filtered delete
- **WHEN** delete evaluates a filtered query
- **THEN** it executes one dialect-safe DELETE and returns the number of affected rows

### Requirement: Mutation safety guards
Bulk mutations SHALL reject ambiguous or dangerous query shapes before execution.

#### Scenario: Missing filter
- **WHEN** update or delete has no WHERE expression
- **THEN** it raises `ValueError`

#### Scenario: Unsupported query state
- **WHEN** update or delete contains ordering, limit, offset, or eager-loading directives
- **THEN** it raises `ValueError`

#### Scenario: Invalid update fields
- **WHEN** update has no values, an unknown field, or a primary-key field
- **THEN** it raises a descriptive error before execution

### Requirement: Mutation state synchronization
Successful bulk mutations SHALL prevent Session caches from returning stale model state.

#### Scenario: Cached model affected
- **WHEN** a bulk statement affects at least one row
- **THEN** Session clears its identity map and second-level cache

### Requirement: Mutation transaction behavior
Bulk mutations SHALL execute inside normal Session transaction behavior and honor Session autocommit.

#### Scenario: Manual transaction
- **WHEN** autocommit is disabled
- **THEN** the caller can commit or roll back the statement normally

#### Scenario: Autocommit
- **WHEN** autocommit is enabled
- **THEN** the statement is committed before the terminal method returns

### Requirement: Bulk-operation boundaries
Bulk mutations SHALL bypass per-instance validation, hooks, managed timestamps, and model hydration.

#### Scenario: Set-based mutation
- **WHEN** update or delete affects rows
- **THEN** no model instances are materialized and no instance lifecycle hooks run

