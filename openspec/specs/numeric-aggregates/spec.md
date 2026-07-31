# numeric-aggregates Specification

## Purpose
TBD - created by archiving change numeric-aggregates. Update Purpose after archive.
## Requirements
### Requirement: Numeric aggregate terminals
QuerySet and QueryManager SHALL expose sum, average, minimum, and maximum terminal operations for numeric model fields.

#### Scenario: Filtered aggregate
- **WHEN** an aggregate evaluates a filtered numeric field
- **THEN** it returns the database-calculated scalar without hydrating models

#### Scenario: Empty aggregate
- **WHEN** no rows enter an aggregate
- **THEN** it returns `None`

### Requirement: Ordered slice semantics
Aggregates SHALL apply query filtering, ordering, limit, and offset before calculating the result.

#### Scenario: Sliced sum
- **WHEN** a sum runs on an ordered limited query
- **THEN** only numeric values in that exact slice contribute to the result

### Requirement: Aggregate validation
Aggregates SHALL validate the selected model field before database execution.

#### Scenario: Unknown field
- **WHEN** an aggregate names an unknown field
- **THEN** it raises the model metadata unknown-field error

#### Scenario: Non-numeric field
- **WHEN** an aggregate names a non-numeric field
- **THEN** it raises `ValueError`

### Requirement: Portable aggregate compilation
Aggregate SQL SHALL use dialect quoting, placeholders, table formatting, and slice syntax.

#### Scenario: Supported dialect
- **WHEN** an aggregate compiles for SQLite, PostgreSQL, or MySQL
- **THEN** the derived query and aggregate use that dialect's SQL conventions

### Requirement: Aggregate session resolution
Aggregates SHALL use the standard explicit or context-bound Session requirement.

#### Scenario: Missing session
- **WHEN** an aggregate evaluates without a bound Session
- **THEN** it raises the standard QuerySet session error

