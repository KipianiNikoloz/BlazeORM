"""
Relationship field implementations and registry utilities.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type

from .fields import Field


class RelationshipError(RuntimeError):
    pass


class RelatedField(Field):
    """
    Base class for relationship fields (FK, O2O).
    """

    relation_type = "many-to-one"

    def __init__(
        self,
        to: Type | str,
        *,
        related_name: Optional[str] = None,
        on_delete: str = "CASCADE",
        db_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("db_type", db_type or "INTEGER")
        super().__init__(**kwargs)
        self.to = to
        self.related_name = related_name
        self.on_delete = on_delete
        self.remote_model: Optional[Type] = to if isinstance(to, type) else None

    def contribute_to_class(self, model: Type, name: str) -> None:
        super().contribute_to_class(model, name)

    def resolve_model(self, model: Type) -> None:
        self.remote_model = model


class ForeignKey(RelatedField):
    relation_type = "many-to-one"

    def __init__(
        self,
        to: Type | str,
        *,
        related_name: Optional[str] = None,
        on_delete: str = "CASCADE",
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("nullable", False)
        super().__init__(to, related_name=related_name, on_delete=on_delete, **kwargs)

    def __set__(self, instance, value):
        if hasattr(value, "pk"):
            value = value.pk
        super().__set__(instance, value)


class OneToOneField(ForeignKey):
    relation_type = "one-to-one"

    def __init__(self, to: Type | str, *, related_name: Optional[str] = None, **kwargs: Any) -> None:
        kwargs.setdefault("unique", True)
        super().__init__(to, related_name=related_name, **kwargs)


class ManyToManyDescriptor:
    def __init__(self, field: "ManyToManyField") -> None:
        self.field = field

    def __get__(self, instance, owner):
        raise NotImplementedError("Many-to-many relations are not implemented yet.")


class ManyToManyField(RelatedField):
    relation_type = "many-to-many"

    def __init__(
        self,
        to: Type | str,
        *,
        related_name: Optional[str] = None,
        through: Optional[str] = None,
        db_table: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("db_type", None)
        kwargs.setdefault("nullable", True)
        kwargs.pop("db_type", None)
        super().__init__(to, related_name=related_name, db_type=None, **kwargs)
        self.through = through
        self.db_table = db_table

    def contribute_to_class(self, model: Type, name: str) -> None:
        self.name = name
        self.model = model
        setattr(model, name, ManyToManyDescriptor(self))


class RelatedAccessor:
    def __init__(self, source_model: Type, field: RelatedField) -> None:
        self.source_model = source_model
        self.field = field

    def __get__(self, instance, owner):
        return RelatedManager(self.source_model, self.field, instance)


class RelatedManager:
    """
    Provides a QuerySet filtered by a parent instance for reverse relations.
    """

    def __init__(self, source_model: Type, field: RelatedField, instance) -> None:
        self.model = source_model
        self.field = field
        self.instance = instance

    def all(self):
        qs = self.model.objects.all()
        if self.instance:
            return qs.filter(**{self.field.name: self.instance.pk})
        return qs

    def filter(self, **lookups):
        return self.all().filter(**lookups)


class RelationRegistry:
    def __init__(self) -> None:
        self.models: Dict[str, Type] = {}
        self.pending_fields: List[Tuple[Type, RelatedField]] = []

    def register_model(self, model: Type) -> None:
        label = self._label(model)
        self.models[label] = model
        self._resolve_pending()

    def register_field(self, model: Type, field: RelatedField) -> None:
        target = self._resolve_target(field.to)
        if target is None:
            self.pending_fields.append((model, field))
            return
        field.resolve_model(target)
        self._attach_reverse_accessor(model, field)

    def _resolve_pending(self) -> None:
        unresolved = []
        for model, field in self.pending_fields:
            target = self._resolve_target(field.to)
            if target is None:
                unresolved.append((model, field))
                continue
            field.resolve_model(target)
            self._attach_reverse_accessor(model, field)
        self.pending_fields = unresolved

    def _resolve_target(self, target: Type | str) -> Optional[Type]:
        if isinstance(target, type):
            return target
        label = target.split(".")[-1]
        return self.models.get(label)

    def _label(self, model: Type) -> str:
        return model.__name__

    def _attach_reverse_accessor(self, model: Type, field: RelatedField) -> None:
        remote = field.remote_model
        if remote is None:
            return
        if isinstance(field, ManyToManyField):
            # ManyToMany reverse managers not implemented yet.
            return
        related_name = field.related_name or f"{model.__name__.lower()}_set"
        if hasattr(remote, related_name):
            return
        descriptor = RelatedAccessor(model, field)
        setattr(remote, related_name, descriptor)


relation_registry = RelationRegistry()
