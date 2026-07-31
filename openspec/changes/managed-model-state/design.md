## Context

Managed timestamps need to be assigned before validation and SQL parameter generation. Refresh must bypass `Session.get()` because primary-key lookups intentionally return identity-map entries without querying the database.

## Goals / Non-Goals

**Goals:**
- Make managed timestamps reflect actual persistence events using timezone-aware UTC values.
- Reload all scalar fields from the database while preserving object identity.
- Remove refreshed instances from pending dirty work and invalidate relation state.

**Non-Goals:**
- Partial refreshes, database-expression defaults, timezone configuration, row locking, or detached-object merging.

## Decisions

1. Session assigns one `datetime.now(timezone.utc)` value per persisted instance. Inserts assign it to both `auto_now` and `auto_now_add`; updates assign it only to `auto_now`. Assignment occurs before validation and hooks observe the managed values.
2. DateTimeField accepts datetime objects and ISO-8601 strings from adapters. Naive values are preserved rather than silently assigning a timezone; Session-generated values are always aware UTC.
3. `Session.refresh(instance)` requires a persisted model with a non-null primary key. It builds a dialect-quoted SELECT through `Session.execute()`, bypassing both cache layers.
4. Refresh mutates `_field_values` on the same object, replaces `_initial_state`, clears `_related_cache`, ensures persisted state, re-adds the identity-map entry, updates second-level cache, and removes the instance from pending dirty registration.
5. Missing rows raise the public `DoesNotExist` exception. New or deleted instances raise `ValueError` before SQL execution.

## Risks / Trade-offs

- Application edits are overwritten by refresh -> this is the method's explicit purpose.
- Adapter datetime representations vary -> ISO parsing covers the textual format emitted by supported adapters while native datetime values pass through.
- Refresh clears all relation caches -> conservative, but prevents stale related objects after scalar reload.

## Migration Plan

The change corrects documented field semantics and adds a method. Existing explicit timestamp fields without managed flags are unchanged.

## Open Questions

None.
