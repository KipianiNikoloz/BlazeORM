## ADDED Requirements

### Requirement: First-result evaluation
QuerySet and QueryManager SHALL expose `first()` and return the first matching model or `None` through the bound session.

#### Scenario: Matching row
- **WHEN** `first()` evaluates a query with at least one row
- **THEN** it returns one materialized model and evaluates no more than one row

#### Scenario: Empty or zero-limited query
- **WHEN** the query has no rows or an effective limit of zero
- **THEN** `first()` returns `None`

### Requirement: Exact-one evaluation
QuerySet and QueryManager SHALL expose `get(**lookups)` and enforce exactly one matching result.

#### Scenario: Exactly one row
- **WHEN** `get()` matches one row
- **THEN** it returns that materialized model

#### Scenario: No rows
- **WHEN** `get()` matches no rows
- **THEN** it raises `DoesNotExist`

#### Scenario: Multiple rows
- **WHEN** `get()` matches more than one row
- **THEN** it raises `MultipleObjectsReturned` after fetching at most two rows

### Requirement: Count evaluation
QuerySet and QueryManager SHALL expose `count()` and return the number of rows represented by the query's filters, limit, and offset without materializing models.

#### Scenario: Filtered and sliced count
- **WHEN** `count()` evaluates a filtered query with limit or offset
- **THEN** it returns the row count after applying that slice and ignores ordering/eager-loading directives

### Requirement: Existence evaluation
QuerySet and QueryManager SHALL expose `exists()` and return whether the filtered, sliced query contains at least one row without materializing models.

#### Scenario: Existing row
- **WHEN** an eligible row exists
- **THEN** `exists()` returns `True` using a one-row probe

#### Scenario: Missing or zero-limited row
- **WHEN** no eligible row exists or the effective limit is zero
- **THEN** `exists()` returns `False`

### Requirement: Public query errors
The package SHALL export `QueryError`, `DoesNotExist`, and `MultipleObjectsReturned` from `blazeorm.query` and the package root.

#### Scenario: Import errors
- **WHEN** a user imports query cardinality exceptions from either public location
- **THEN** the same exception classes are available

### Requirement: Session requirement
All terminal operations that access the database SHALL use an explicitly bound or context-bound Session and fail clearly when none is available.

#### Scenario: Unbound terminal operation
- **WHEN** a terminal method needs database access without a bound Session
- **THEN** it raises the same descriptive runtime error used by QuerySet iteration
