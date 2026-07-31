## ADDED Requirements

### Requirement: Creation timestamps
Session SHALL assign a timezone-aware UTC timestamp to `auto_now_add` fields when inserting a model and SHALL preserve that value on later updates.

#### Scenario: Insert then update
- **WHEN** a model with `auto_now_add` is inserted and later updated
- **THEN** its creation timestamp is assigned on insert and remains unchanged by the update

### Requirement: Modification timestamps
Session SHALL assign a timezone-aware UTC timestamp to `auto_now` fields on every insert and effective update.

#### Scenario: Updating a model
- **WHEN** a persisted model with `auto_now` is saved after a field change
- **THEN** its modification timestamp advances and is included in validation, hooks, and update SQL

### Requirement: Datetime hydration
DateTimeField SHALL hydrate native datetime objects and ISO-formatted datetime strings returned by supported adapters.

#### Scenario: Text datetime value
- **WHEN** an adapter returns an ISO-formatted stored timestamp
- **THEN** materialization exposes it as a datetime instance

### Requirement: Refresh persisted instance
Session SHALL expose `refresh(instance)` to reload all scalar fields by primary key while preserving Python object identity.

#### Scenario: Database value changed externally
- **WHEN** refresh is called after the row changes in the database
- **THEN** the same model object contains current field values and a clean initial-state snapshot

#### Scenario: Cached relations and dirty registration
- **WHEN** refresh succeeds for an instance with cached relations or pending dirty registration
- **THEN** relation caches are cleared and the pending dirty registration is removed

### Requirement: Refresh errors
Refresh SHALL reject instances that cannot identify an existing persisted row.

#### Scenario: New or deleted instance
- **WHEN** refresh receives an instance not currently marked persisted or without a primary-key value
- **THEN** it raises `ValueError` without querying

#### Scenario: Missing database row
- **WHEN** the persisted instance's row no longer exists
- **THEN** refresh raises `DoesNotExist`

### Requirement: Cross-dialect state management
Timestamp persistence and refresh SHALL use existing Session, adapter, and dialect boundaries.

#### Scenario: Supported backend
- **WHEN** managed state operates on SQLite, PostgreSQL, or MySQL
- **THEN** identifier quoting, placeholders, execution, transactions, and value normalization remain dialect- and adapter-controlled
