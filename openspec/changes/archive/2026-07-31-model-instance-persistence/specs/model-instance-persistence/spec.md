## ADDED Requirements

### Requirement: Save new model instances
Model instances SHALL expose `save(session=None)` and register a new instance with the resolved Session.

#### Scenario: Explicit session
- **WHEN** a new instance calls `save(session=session)`
- **THEN** it is inserted through that Session and receives any database-assigned primary key on flush or commit

#### Scenario: Application-assigned primary key
- **WHEN** a new instance already has a primary-key value and calls `save()`
- **THEN** it is treated as new and inserted rather than updated

### Requirement: Save persisted model instances
A model materialized or successfully inserted by Session SHALL be treated as persisted and `save()` SHALL register its changes as dirty.

#### Scenario: Updating a loaded model
- **WHEN** a loaded model changes and calls `save()`
- **THEN** Session updates its changed fields through the normal validation, hook, identity-map, and cache path

#### Scenario: Autocommit update
- **WHEN** a persisted model calls `save()` through an autocommit Session
- **THEN** the update is committed without a separate commit call

### Requirement: Delete persisted model instances
Model instances SHALL expose `delete(session=None)` and delete persisted instances through the resolved Session.

#### Scenario: Deleting a loaded model
- **WHEN** a persisted instance calls `delete()`
- **THEN** Session runs delete hooks, removes the row, and invalidates identity-map and cache entries

#### Scenario: Deleting a new model
- **WHEN** an instance that has never been persisted calls `delete()`
- **THEN** it raises `ValueError` without registering a delete

### Requirement: Session resolution
Instance persistence methods SHALL prefer an explicit Session and otherwise use the context-bound Session.

#### Scenario: Context-bound session
- **WHEN** save or delete is called inside a Session context without an explicit session
- **THEN** the current Session performs the operation

#### Scenario: Missing session
- **WHEN** save or delete is called without an explicit or context-bound Session
- **THEN** it raises a descriptive `RuntimeError`

### Requirement: Cross-dialect persistence path
Instance persistence SHALL reuse Session persistence and adapter/dialect behavior without backend-specific model logic.

#### Scenario: Non-SQLite backend
- **WHEN** instance persistence runs with PostgreSQL or MySQL adapters
- **THEN** SQL quoting, placeholders, execution, transactions, validation, and hooks remain controlled by the existing Session and dialect paths
