# portable-query-lookups Specification

## Purpose
TBD - created by archiving change portable-query-lookups. Update Purpose after archive.
## Requirements
### Requirement: Collection membership lookup
The query compiler SHALL compile `field__in` with one dialect placeholder per supplied value and SHALL reject scalar strings, bytes, and non-iterable values.

#### Scenario: Non-empty collection
- **WHEN** a QuerySet filters a field with a non-empty iterable
- **THEN** the compiler emits an `IN` expression with matching parameters in iteration order

#### Scenario: Empty collection
- **WHEN** a QuerySet filters a field with an empty iterable
- **THEN** the compiler emits an always-false expression with no parameters

### Requirement: Null-state lookup
The query compiler SHALL compile `field__isnull=True` as `IS NULL` and `field__isnull=False` as `IS NOT NULL`, and SHALL reject non-boolean values.

#### Scenario: Null requested
- **WHEN** `isnull` receives `True`
- **THEN** the SQL tests the field with `IS NULL` and supplies no parameter

#### Scenario: Non-null requested
- **WHEN** `isnull` receives `False`
- **THEN** the SQL tests the field with `IS NOT NULL` and supplies no parameter

### Requirement: Portable text lookups
The query compiler SHALL support `startswith`, `endswith`, and `icontains`, and SHALL compile `iexact` and `icontains` with `LOWER(column)` and normalized parameters for consistent behavior across SQLite, PostgreSQL, and MySQL.

#### Scenario: Prefix and suffix
- **WHEN** `startswith` or `endswith` receives a string
- **THEN** the compiler emits a parameterized `LIKE` expression with the wildcard on the correct side

#### Scenario: Case-insensitive text
- **WHEN** `iexact` or `icontains` receives a string
- **THEN** the compiler applies `LOWER` to the column and lowercases the bound value

#### Scenario: Invalid text value
- **WHEN** a text-specific lookup receives a non-string value
- **THEN** compilation raises a descriptive `ValueError`

### Requirement: Dialect portability
Every new lookup SHALL use the active dialect's identifier quoting and parameter placeholder.

#### Scenario: Supported dialect compilation
- **WHEN** the same lookup is compiled with SQLite, PostgreSQL, and MySQL dialects
- **THEN** identifiers and placeholders match each selected dialect while parameters remain equivalent

