## Context

QuerySet currently compiles one SELECT shape and evaluates only through iteration. `Session.get()` supports one filter but does not compose with QuerySet state. Count and existence checks should execute minimal SQL while retaining dialect-specific slicing.

## Goals / Non-Goals

**Goals:**
- Add familiar terminal APIs with explicit cardinality semantics.
- Preserve filters, limits, offsets, session materialization, and identity-map reuse.
- Avoid model hydration for count and existence checks.

**Non-Goals:**
- Bulk mutations, query-result caching, async behavior, or Session API replacement.

## Decisions

1. Define `QueryError`, `DoesNotExist`, and `MultipleObjectsReturned` in the QuerySet module and re-export them. Dedicated errors let callers distinguish cardinality failures from connection or validation failures.
2. Extract `_require_session()` and `_evaluate()` from iteration. `_evaluate(max_results=None)` compiles and materializes through the session, retaining eager loading. `first()` uses an effective limit of one; `get()` applies lookups, overrides the limit to two, and preserves offset.
3. Add compiler methods for count and existence probes. Each builds an inner `SELECT 1` using FROM/WHERE and existing limit/offset but no ordering or eager-loading joins. Count wraps it in `SELECT COUNT(*)`; exists forces an effective maximum of one row. Derived tables are supported by all three databases and preserve slice semantics.
4. Return `0`/`False` without executing SQL for `limit(0)`. All other terminal operations resolve a session using the same helper as iteration.
5. QueryManager delegates to a fresh QuerySet, keeping context-bound behavior identical to existing manager methods.

## Risks / Trade-offs

- Derived-table count SQL is more verbose than a direct aggregate -> It correctly preserves offset/limit and is portable.
- `get()` overrides an existing positive limit -> Required to detect multiple matches; offset remains part of the query.
- Unordered `first()` follows database row order -> Matches current QuerySet ordering semantics; callers can use `order_by()` for determinism.

## Migration Plan

The API is additive. Reverting the QuerySet/compiler and export changes restores the previous surface.

## Open Questions

None.
