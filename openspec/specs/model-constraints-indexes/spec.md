# model-constraints-indexes Specification

## Purpose
TBD - created by archiving change model-constraints-indexes. Update Purpose after archive.
## Requirements
### Requirement: Public constraint metadata
The package SHALL export immutable `UniqueConstraint` and `Index` metadata objects from `blazeorm.core` and the package root.

#### Scenario: Metadata construction
- **WHEN** metadata is created with one or more distinct non-empty field names and an optional name
- **THEN** it preserves the ordered field tuple and cannot be mutated

#### Scenario: Invalid metadata fields
- **WHEN** metadata receives no fields, duplicate fields, or empty/non-string names
- **THEN** construction raises `ValueError`

### Requirement: Model metadata collection
Model Meta SHALL accept ordered constraints and indexes and expose them through ModelOptions.

#### Scenario: Concrete declaration
- **WHEN** a concrete model declares Meta constraints or indexes
- **THEN** ModelOptions retains them in declaration order

#### Scenario: Abstract inheritance
- **WHEN** abstract bases declare constraints or indexes
- **THEN** concrete descendants inherit those entries before local entries

### Requirement: Model metadata validation
Model construction SHALL reject invalid constraint and index references.

#### Scenario: Unknown or many-to-many field
- **WHEN** metadata references a missing or many-to-many field
- **THEN** class creation raises ModelConfigurationError

#### Scenario: Duplicate definition or name
- **WHEN** metadata repeats a definition or explicit name in its category
- **THEN** class creation raises ModelConfigurationError

### Requirement: Unique constraint SQL
SchemaBuilder SHALL render model UniqueConstraint entries inside portable CREATE TABLE SQL.

#### Scenario: Named composite uniqueness
- **WHEN** a constraint covers multiple fields
- **THEN** CREATE TABLE contains a dialect-quoted named UNIQUE clause with columns in declaration order

#### Scenario: Generated constraint name
- **WHEN** no name is supplied
- **THEN** SchemaBuilder generates a deterministic table-and-column-based name

### Requirement: Composite index SQL
SchemaBuilder SHALL include model Index entries in create and drop index statements.

#### Scenario: Supported dialect
- **WHEN** composite index SQL is generated for SQLite, PostgreSQL, or MySQL
- **THEN** table, index, and ordered columns use dialect syntax and deterministic or explicit names

### Requirement: Explicit migration boundary
Constraint and index metadata SHALL not mutate database schema automatically.

#### Scenario: Model declaration
- **WHEN** metadata is attached to a model
- **THEN** schema changes occur only when generated DDL is placed in explicit migration operations

