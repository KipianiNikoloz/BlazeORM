## Context

`SQLCompiler._compile_lookup()` currently maps simple lookup names to operators. `iexact` lowercases only the parameter, making its result backend-dependent. Collection and null-state operators need dedicated compilation because their placeholder counts and parameter rules differ from scalar comparisons.

## Goals / Non-Goals

**Goals:**
- Provide deterministic lookup validation and parameterized SQL.
- Keep quoting and placeholders dialect-owned.
- Preserve the existing QuerySet API and expression-tree behavior.

**Non-Goals:**
- Relationship traversal, wildcard escaping, backend-native case-insensitive operators, or arbitrary expressions.

## Decisions

1. Keep lookup compilation in `SQLCompiler`. It already owns field resolution and dialect rendering; moving lookup policy into QuerySet or adapters would split SQL responsibilities.
2. Handle `in` and `isnull` before the scalar operator table. `in` materializes a non-string iterable once, emits one placeholder per value, and maps an empty iterable to `1 = 0`. `isnull` accepts exact booleans only.
3. Define text lookups explicitly. `startswith`, `endswith`, and `contains` use `LIKE`; `iexact` and `icontains` use `LOWER(quoted_column)` with lowercase string parameters. Text-specific lookups reject non-strings.
4. Retain parameter binding for every user value. The only literal expression is the value-independent empty-collection false predicate.
5. Test SQL generation under each dialect rather than depending on one database's collation behavior.

## Risks / Trade-offs

- `LOWER` can prevent use of a plain index -> Users can add an expression index outside BlazeORM when needed; portability is prioritized.
- `%` and `_` in values remain SQL wildcard characters -> Documented as existing LIKE semantics; escaping is a separate capability.
- Iterables such as generators are consumed during compilation -> Materialize exactly once and retain parameter order.

## Migration Plan

This is additive except for correcting `iexact`. Existing code needs no migration. Reverting the compiler and documentation commits restores prior behavior.

## Open Questions

None.
