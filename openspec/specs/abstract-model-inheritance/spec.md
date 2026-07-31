# abstract-model-inheritance Specification

## Purpose
TBD - created by archiving change abstract-model-inheritance. Update Purpose after archive.
## Requirements
### Requirement: Abstract field inheritance
A model SHALL inherit cloned fields from each ancestor model marked abstract and SHALL NOT inherit fields from concrete model bases.

#### Scenario: Concrete descendant
- **WHEN** a concrete model subclasses an abstract model containing scalar fields
- **THEN** its metadata, initialization, validation, persistence, and generated schema include independent copies of those fields

#### Scenario: Abstract chain
- **WHEN** an abstract model subclasses another abstract model
- **THEN** a later concrete descendant receives fields from the full abstract chain in declaration order

### Requirement: Relationship inheritance
Foreign-key, one-to-one, and many-to-many fields inherited from abstract bases SHALL retain their configuration and SHALL be rebound and registered for the concrete descendant.

#### Scenario: Inherited relations
- **WHEN** a concrete model inherits abstract relationship fields
- **THEN** forward descriptors, reverse accessors, schema metadata, and custom through-table settings reference the concrete descendant's cloned fields

### Requirement: Field isolation
Every descendant SHALL own distinct field objects so binding or mutating one model's metadata cannot alter its abstract base or sibling descendants.

#### Scenario: Sibling descendants
- **WHEN** two concrete models inherit the same abstract field
- **THEN** each field has the correct owning model and changing one field's metadata does not change the other

### Requirement: Overrides and conflicts
A field declared on the subclass SHALL override an inherited field of the same name. Duplicate inherited names from multiple abstract bases SHALL raise `ModelConfigurationError` unless explicitly overridden by the subclass.

#### Scenario: Explicit override
- **WHEN** a subclass declares a field with an inherited name
- **THEN** only the declared field appears in its metadata at that inherited position

#### Scenario: Unresolved multiple-base conflict
- **WHEN** abstract bases contribute different fields with the same name and the subclass does not override it
- **THEN** model construction raises `ModelConfigurationError` naming the field

### Requirement: Primary-key behavior
Abstract models SHALL NOT receive an automatic primary key. Concrete descendants SHALL retain an inherited explicit primary key or receive one automatic `id` field when none exists.

#### Scenario: Concrete automatic key
- **WHEN** inherited and declared fields contain no primary key
- **THEN** the concrete model receives exactly one automatic `id` primary key before other fields

#### Scenario: Inherited explicit key
- **WHEN** an abstract base defines a primary key
- **THEN** the concrete descendant uses its cloned key and receives no automatic `id`

