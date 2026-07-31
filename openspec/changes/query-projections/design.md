## Context

QuerySet evaluation currently compiles a full model select and materializes every row. Projection queries need the same FROM/WHERE/ORDER/LIMIT pipeline with a caller-selected base column list.

## Goals / Non-Goals

**Goals:** efficient typed field selection, deterministic result shapes, manager parity, and cross-dialect compilation.

**Non-Goals:** relations, annotations, aliases, async/streaming behavior, or returning another chainable QuerySet.

## Decisions

1. Projection methods are terminal and return concrete lists. This avoids introducing a second lazy result type.
2. SQLCompiler exposes `compile_projection(fields)` and shares its SELECT tail assembly with normal compilation. Fields resolve through model metadata and use database column names in SQL.
3. `values()` maps each row to requested model field names in request order. `values_list()` maps positionally; `flat=True` requires exactly one field.
4. Both methods require at least one field and validate every name before database execution. Relationship traversal syntax is not accepted.
5. Projection evaluation ignores select/prefetch-related directives because no models are hydrated, while ordinary query filters, ordering, limit, and offset remain effective.

## Risks / Trade-offs

- Concrete lists may allocate memory for large results -> consistent with current eager terminal methods; streaming is deferred.
- Related fields return stored foreign-key values -> predictable base-column behavior without implicit joins.
- Eager-loading directives are ignored -> avoids surprising model work and matches projection intent.

## Migration Plan

The methods are additive and require no data migration.

## Open Questions

None.
