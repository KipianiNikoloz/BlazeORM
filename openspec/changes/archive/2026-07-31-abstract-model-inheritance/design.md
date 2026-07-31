## Context

`ModelMeta` collects only fields declared in the immediate class and contains a TODO for abstract inheritance. Field objects are mutable descriptors bound to one model, so reusing them would corrupt base/sibling metadata. Scalar subclasses already provide clone support, but relation fields need configuration-aware clones.

## Goals / Non-Goals

**Goals:**
- Make existing `Meta.abstract` semantics useful and deterministic.
- Clone all inherited field types and register relations as fresh fields.
- Preserve order, override rules, validation, schema generation, and PK behavior.

**Non-Goals:**
- Concrete/multi-table inheritance, polymorphism, proxy models, or Meta option inheritance.

## Decisions

1. Collect abstract ancestors from base MRO before binding immediate declarations. Only bases with `_meta.abstract` contribute fields or many-to-many fields. Concrete bases contribute no fields.
2. Clone inherited fields, never reuse descriptors. Add `clone()` implementations to `RelatedField`/`ManyToManyField` that preserve target, related name, delete rule, through/table settings, defaults, validators, and database metadata. A clone starts unbound and relation resolution follows the normal registry.
3. Merge inherited names in deterministic base order. Identical names from multiple contributing bases are an error unless the immediate subclass declares that name; an override replaces the inherited slot rather than moving to the end.
4. Allow abstract-to-abstract chains to accumulate cloned metadata. Automatic keys remain disabled for every abstract class and are added only to concrete descendants without a primary key.
5. Use the existing contribution and relation-registry paths for inherited clones so descriptors, reverse accessors, eager loading, and schema generation do not gain a parallel implementation.

## Risks / Trade-offs

- Relation registry contains global class state -> Tests use unique model names and assert each clone is registered to its owner.
- Callable defaults and validator objects are shared by shallow clone -> They are immutable/callable configuration; validator lists themselves are copied.
- Multiple-base conflict rules are stricter than Python's first-base wins -> Explicit failure prevents silent schema changes.

## Migration Plan

The behavior is additive for classes already marked abstract. Such subclasses will begin receiving previously ignored fields, which is the intended meaning of the existing flag. Revert the metaclass and clone changes to roll back.

## Open Questions

None.
