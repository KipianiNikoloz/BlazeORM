## ADDED Requirements

### Requirement: Dictionary projections
QuerySet and QueryManager SHALL expose `values(*fields)` and return one dictionary per selected row keyed by requested model field name.

#### Scenario: Filtered and ordered projection
- **WHEN** values evaluates selected fields on a filtered, ordered, and sliced query
- **THEN** it returns only those fields in query result order while preserving the query constraints

### Requirement: Tuple projections
QuerySet and QueryManager SHALL expose `values_list(*fields, flat=False)` and return positional tuples by default.

#### Scenario: Multiple fields
- **WHEN** two or more fields are selected
- **THEN** each result is a tuple whose positions match request order

#### Scenario: Flat single field
- **WHEN** one field is selected with `flat=True`
- **THEN** each result is the scalar field value

### Requirement: Projection validation
Projection methods SHALL validate result shape and field names before database execution.

#### Scenario: No fields
- **WHEN** either projection method receives no fields
- **THEN** it raises `ValueError`

#### Scenario: Unknown field
- **WHEN** a projection names a field absent from model metadata
- **THEN** it raises the model's descriptive unknown-field error

#### Scenario: Invalid flat shape
- **WHEN** `flat=True` is combined with anything other than exactly one field
- **THEN** it raises `ValueError`

### Requirement: Projection execution isolation
Projection methods SHALL execute through the resolved Session without materializing models or changing identity and relation caches.

#### Scenario: Projection evaluation
- **WHEN** a projection returns rows
- **THEN** it uses dialect-safe SQL and leaves the Session identity map unchanged

#### Scenario: Missing session
- **WHEN** a projection is evaluated without an explicit or context-bound Session
- **THEN** it raises the standard QuerySet session error
