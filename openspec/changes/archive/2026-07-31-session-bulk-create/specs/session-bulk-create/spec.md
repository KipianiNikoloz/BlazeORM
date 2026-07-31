## ADDED Requirements

### Requirement: Atomic bulk creation
Session SHALL expose `bulk_create(instances)` and atomically persist homogeneous new model instances in input order.

#### Scenario: Successful collection
- **WHEN** valid new instances are bulk-created
- **THEN** all rows are committed together and the same instances are returned in input order

#### Scenario: Empty collection
- **WHEN** bulk_create receives no instances
- **THEN** it returns an empty list without opening a transaction

### Requirement: Normal creation lifecycle
Bulk creation SHALL reuse normal Session creation semantics for every instance.

#### Scenario: Generated keys and managed fields
- **WHEN** instances use generated primary keys or managed timestamps
- **THEN** each object receives persisted values and becomes available through identity and second-level caches

#### Scenario: Validation and hooks
- **WHEN** instances are created successfully
- **THEN** normal validation and before/after-save hooks run once per instance in input order

### Requirement: Bulk input validation
Bulk creation SHALL reject invalid collection shapes before writing rows.

#### Scenario: Mixed models
- **WHEN** instances have different concrete model classes
- **THEN** bulk_create raises `ValueError`

#### Scenario: Existing or duplicate instance
- **WHEN** an instance is already persisted or the same object appears more than once
- **THEN** bulk_create raises `ValueError`

#### Scenario: Non-model input
- **WHEN** a collection item is not a Model
- **THEN** bulk_create raises `TypeError`

### Requirement: Failure restoration
Bulk creation SHALL roll back database writes and restore all input object state when any operation fails.

#### Scenario: Later instance fails
- **WHEN** validation, hooks, SQL, or commit fails after an earlier insert
- **THEN** no collection row remains committed and every input object matches its pre-call scalar and lifecycle state

### Requirement: Nested transaction compatibility
Bulk creation SHALL use a savepoint when a Session transaction is already active.

#### Scenario: Outer transaction
- **WHEN** bulk_create succeeds inside an outer transaction
- **THEN** generated values are available but the outer transaction still controls final commit or rollback
