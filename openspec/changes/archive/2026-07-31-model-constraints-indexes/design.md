## Context

ModelOptions already centralizes bound fields, and SchemaBuilder renders tables plus field-level indexes. Composite metadata belongs in core but SQL rendering remains in schema/dialect boundaries.

## Goals / Non-Goals

**Goals:** immutable public metadata, early model validation, abstract inheritance, deterministic names, and portable create/drop SQL.

**Non-Goals:** partial/expression/check/exclusion constraints, backend-specific index options, introspection, schema diffing, or implicit migration execution.

## Decisions

1. Add frozen dataclasses `UniqueConstraint(fields, name=None)` and `Index(fields, name=None)` in `core.constraints`. Constructors require at least one unique non-empty string field name.
2. ModelOptions stores ordered tuples. ModelMeta concatenates metadata from abstract bases before locally declared Meta entries, mirroring field inheritance.
3. After all fields bind, ModelMeta validates that every reference names a scalar field, definitions are not duplicated, and explicit names do not collide within constraints or indexes. Invalid configuration raises ModelConfigurationError.
4. SchemaBuilder appends unique constraints to CREATE TABLE. Missing names become `uq_<table>_<columns>`; explicit/generated names and identifiers are dialect-quoted.
5. `create_index_sql` and `drop_index_sql` include composite Index entries in addition to field indexes. Missing names become `idx_<table>_<columns>` and MySQL keeps its required DROP INDEX ... ON table syntax.
6. The cumulative release version becomes 0.4.0 and `uv.lock` is regenerated because the local project version is part of the lock.

## Risks / Trade-offs

- Generated names may exceed backend identifier limits for unusually long names -> explicit names provide control; truncation/collision policy is deferred.
- Abstract-base metadata can collide -> class creation fails early and requires the concrete model to define unambiguous metadata.
- Existing explicit migration workflows remain manual -> metadata improves DDL generation without introducing unsafe automatic migrations.

## Migration Plan

The API is additive. Applications opt in by adding Meta metadata and explicit migration operations using generated SQL.

## Open Questions

None.
