## Context

Set-based mutations should reuse Q compilation and Session execution but cannot safely synchronize individual loaded models without fetching every affected row.

## Goals / Non-Goals

**Goals:** guarded SQL generation, explicit limitations, transaction compatibility, affected counts, and stale-cache prevention.

**Non-Goals:** per-instance hooks/validation, managed timestamps, relationship joins, SQL expressions, returning clauses, or automatic cascades.

## Decisions

1. QuerySet exposes terminal `update(**values)` and `delete()`. QueryManager does not expose direct shortcuts because an unfiltered manager mutation is prohibited; callers use `Model.objects.filter(...)`.
2. Both methods require a non-empty Q tree. They reject order, limit, offset, select_related, and prefetch_related state rather than pretending those clauses constrain portable UPDATE/DELETE statements.
3. Compiler update validates non-empty fields, metadata names, and primary-key immutability. QuerySet normalizes values through Session before compiling parameters.
4. After a statement affects rows, Session clears the identity map and second-level cache because determining the precise affected cached keys would require a pre-query and race-prone synchronization.
5. Autocommit Session commits immediately; otherwise the mutation remains in the current database transaction. No per-instance hooks, full_clean, or managed timestamps run.

## Risks / Trade-offs

- Clearing the complete session cache is conservative -> guarantees no stale objects after arbitrary predicates.
- Requiring filters blocks intentional table-wide maintenance -> raw Session SQL remains available for explicit administrative work.
- Hook bypass differs from instance operations -> documented and consistent with set-based performance goals.

## Migration Plan

The API is additive. Existing raw SQL continues to work.

## Open Questions

None.
