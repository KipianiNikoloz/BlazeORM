# transaction-state-rollback Specification

## Purpose
TBD - created by archiving change transaction-state-rollback. Update Purpose after archive.
## Requirements
### Requirement: Flushed update restoration
Session rollback SHALL restore ORM-managed scalar and clean-state values captured at transaction entry.

#### Scenario: Dirty model flushed then rolled back
- **WHEN** a loaded model is changed, flushed, and rolled back
- **THEN** the database and the same Python object both expose the transaction-entry values and the object is clean

### Requirement: Insert lifecycle restoration
Session rollback SHALL restore new objects to their pre-transaction lifecycle and generated-key state.

#### Scenario: New object flushed then rolled back
- **WHEN** an object receives a generated primary key during a transaction that rolls back
- **THEN** its key, persisted flag, identity-map membership, and registration return to their entry state

### Requirement: Delete lifecycle restoration
Session rollback SHALL restore deleted objects that existed at transaction entry.

#### Scenario: Delete flushed then rolled back
- **WHEN** a persisted object is deleted and the transaction rolls back
- **THEN** it is marked persisted again and restored to its prior identity-map membership

### Requirement: Late participant capture
Instances first registered after transaction entry SHALL still be restored to their pre-registration state.

#### Scenario: Add after begin
- **WHEN** a new object is added and flushed after begin
- **THEN** rollback removes generated state even though the object was absent from the initial Session snapshot

### Requirement: Nested state boundaries
Each nested transaction SHALL restore to its own entry state independently.

#### Scenario: Inner rollback then outer commit
- **WHEN** an inner savepoint changes and flushes a model before rolling back
- **THEN** the model returns to its outer-transaction value and the outer transaction can commit that value

#### Scenario: Inner commit then outer rollback
- **WHEN** an inner savepoint commits model changes but the outer transaction rolls back
- **THEN** the model returns to the outer transaction's entry state

### Requirement: Cache rollback consistency
Rollback SHALL prevent identity and second-level caches from exposing uncommitted state.

#### Scenario: Rolled-back persistence
- **WHEN** inserts, updates, or deletes publish cache changes before rollback
- **THEN** caches are cleared and reconstructed only from persisted transaction-entry identity members

