## Why

BlazeORM's query language lacks common collection, null, and prefix/suffix lookups, while its existing `iexact` behavior is only accidentally case-insensitive on some databases. A portable lookup contract makes everyday filtering useful and consistent across all supported dialects.

## What Changes

- Add `in`, `isnull`, `startswith`, `endswith`, and `icontains` field lookups.
- Make `iexact` explicitly case-insensitive on SQLite, PostgreSQL, and MySQL.
- Define validation for empty collections, scalar strings passed to `in`, non-boolean `isnull` values, and non-string text lookup values.
- Preserve current lookup syntax and parameterized SQL behavior; there are no breaking changes.
- Non-goals: relationship traversal, arbitrary SQL expressions, wildcard escaping, and backend-specific operators.

## Capabilities

### New Capabilities

- `portable-query-lookups`: Cross-dialect compilation and validation for scalar query lookups.

### Modified Capabilities

None.

## Impact

The query compiler and its unit tests change. Public QuerySet filter syntax, query documentation, and the changelog gain the new lookups. No dependencies, schema behavior, or persistence interfaces change.
