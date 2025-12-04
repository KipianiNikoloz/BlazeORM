Core Models, Fields, and Relations
==================================

What Lives Here
---------------
- `model.py`: Declarative model base with metaclass building `_meta`, auto PKs, QueryManager binding, validation hooks, and m2m sugar helpers.
- `fields.py`: Typed fields (Integer, Float, String, Boolean, DateTime, Auto) with defaults, db types, validation, and descriptors.
- `relations.py`: Relationship fields (ForeignKey, OneToOneField, ManyToManyField), reverse accessors, relation registry, m2m managers, and descriptors.
- `validators.py`: Built-in validators and exceptions.

Key Behaviors
-------------
- Models collect `Field` instances at class creation; primary key is auto-added when absent.
- Relationships:
  - FK/O2O store FK values and cache related instances when assigned.
  - M2M installs forward and reverse descriptors backed by `ManyToManyManager` (supports `add/remove/clear`, iteration, and Session-aware fetching).
  - RelationRegistry tracks forward and reverse relations for select_related/prefetch and reverse lookups.
- Validation:
  - `Model.full_clean()` runs field validators and model `clean()` hook.
- Hooks:
  - `Model.register_hook` attaches handlers to lifecycle events (validate/save/delete/commit).

Usage Notes
-----------
- Access m2m relations only within an active `Session` context; managers rely on the current session for queries.
- Use `Model.m2m_add/remove/clear` (or Session helpers) to mutate m2m relations and keep caches coherent.
- Reverse accessors default to `<model>_set` when `related_name` is not provided.

Testing References
------------------
- `tests/core/test_model.py`, `tests/relations/test_relationships.py`, `tests/persistence/test_many_to_many.py`, `tests/query/test_queryset_execution.py`.

