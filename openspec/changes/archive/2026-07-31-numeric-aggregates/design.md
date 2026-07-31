## Context

Count and existence probes already compile terminal SQL. Numeric aggregates additionally need to preserve ordering when a limit or offset determines which values enter the calculation.

## Goals / Non-Goals

**Goals:** portable numeric aggregation, exact slice semantics, explicit validation, and manager parity.

**Non-Goals:** grouping, annotations, arithmetic expressions, joins, or backend-specific statistical functions.

## Decisions

1. SQLCompiler exposes `compile_aggregate(function, field_name)`. It selects the requested column as `blaze_value` in an inner query, retaining WHERE, ORDER BY, LIMIT, and OFFSET, then applies the whitelisted aggregate in an outer query.
2. Public names are `sum`, `average`, `minimum`, and `maximum`; SQL functions are `SUM`, `AVG`, `MIN`, and `MAX`.
3. Only AutoField, IntegerField, and FloatField are accepted. Unknown fields retain metadata's descriptive KeyError; non-numeric fields raise ValueError.
4. Empty inputs return `None`, matching SQL aggregate semantics. Numeric adapter results are returned without lossy coercion.
5. Evaluation uses the standard explicit/context Session resolution and does not hydrate models or populate caches.

## Risks / Trade-offs

- Derived tables are more verbose -> they preserve ordered slicing portably across all supported databases.
- Return types depend on backend numeric behavior -> avoids incorrect conversion and is documented as int, float, or None.

## Migration Plan

The API is additive and needs no migration.

## Open Questions

None.
