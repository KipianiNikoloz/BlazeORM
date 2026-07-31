## Context

Database rollback and the in-memory unit of work form one consistency boundary. Current snapshots hold only three registration sets, while persistence helpers mutate model fields, lifecycle flags, identity maps, and caches during flush.

## Goals / Non-Goals

**Goals:** restore observable model state after rollback, preserve nested boundaries, remove uncommitted identity/cache entries, and retain pre-transaction registrations.

**Non-Goals:** snapshotting arbitrary subclass attributes, transactional guarantees for shared remote caches, inter-Session synchronization, or changing adapter transactions.

## Decisions

1. Replace tuple snapshots with private dataclasses for model state and Session state. A model state copies `_field_values`, `_initial_state`, `_related_cache`, and `_persisted`.
2. At every begin, snapshot all identity-map and currently registered UoW instances plus identity-map membership.
3. Registration methods capture a previously unseen instance into every active snapshot before changing UoW membership. Bulk-create direct persistence does the same after opening its transaction.
4. Rollback restores every captured model, restores UoW sets, rebuilds identity-map membership from the snapshot, clears second-level cache, and repopulates it for persisted snapshot identity members.
5. Nested snapshots are independent. Committing an inner savepoint discards only its snapshot; the outer snapshot remains authoritative for a later outer rollback.

## Risks / Trade-offs

- Snapshots copy model dictionaries -> bounded by models participating in one Session transaction and preferable to inconsistent state.
- Clearing the full second-level cache is conservative -> remote caches cannot provide atomic rollback, but clearing prevents this Session from publishing known stale entries.
- Arbitrary subclass attributes are not restored -> only ORM-managed state participates in persistence semantics.

## Migration Plan

The change is internal and takes effect for new transactions without data migration.

## Open Questions

None.
