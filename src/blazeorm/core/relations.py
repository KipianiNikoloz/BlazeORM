"""
Relationship field implementations and registry utilities.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

from .fields import Field

if TYPE_CHECKING:
    from .model import Model


class RelationshipError(RuntimeError):
    pass


class RelatedField(Field):
    """
    Base class for relationship fields (FK, O2O).
    """

    relation_type = "many-to-one"

    def __init__(
        self,
        to: Type["Model"] | str,
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
        self.remote_model: Optional[Type["Model"]] = to if isinstance(to, type) else None

    def contribute_to_class(self, model: Type["Model"], name: str) -> None:
        super().contribute_to_class(model, name)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        cache = getattr(instance, "_related_cache", {})
        name = self.require_name()
        if name in cache:
            return cache[name]
        return super().__get__(instance, owner)

    def resolve_model(self, model: Type["Model"]) -> None:
        self.remote_model = model


class ForeignKey(RelatedField):
    relation_type = "many-to-one"

    def __init__(
        self,
        to: Type["Model"] | str,
        *,
        related_name: Optional[str] = None,
        on_delete: str = "CASCADE",
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("nullable", False)
        super().__init__(to, related_name=related_name, on_delete=on_delete, **kwargs)

    def __set__(self, instance, value):
        name = self.require_name()
        if hasattr(value, "pk"):
            if hasattr(instance, "_related_cache"):
                instance._related_cache[name] = value
            value = value.pk
        else:
            if hasattr(instance, "_related_cache"):
                instance._related_cache.pop(name, None)
        super().__set__(instance, value)


class OneToOneField(ForeignKey):
    relation_type = "one-to-one"

    def __init__(
        self, to: Type["Model"] | str, *, related_name: Optional[str] = None, **kwargs: Any
    ) -> None:
        kwargs.setdefault("unique", True)
        super().__init__(to, related_name=related_name, **kwargs)


class ManyToManyManager:
    """
    Manager for many-to-many relations supporting read and mutation helpers.
    """

    def __init__(
        self,
        field: "ManyToManyField",
        instance,
        source_model: Type["Model"],
        accessor_name: str,
    ) -> None:
        self.field = field
        self.instance = instance
        self.source_model = source_model
        self.accessor_name = accessor_name
        self.is_reverse = isinstance(instance, field.remote_model) if field.remote_model else False

    def _session(self):
        from ..persistence.session import Session

        session = Session.current()
        if session is None:
            raise RuntimeError("Many-to-many access requires an active Session context.")
        return session

    def _through_table(self) -> str:
        return self.field.through_table(self._field_model())

    def _left_column(self) -> str:
        # Column for the declaring model (field.model)
        return self.field.left_column(self._field_model())

    def _right_column(self) -> str:
        # Column for the related model (remote_model)
        return self.field.right_column(self._field_model())

    def _field_model(self) -> Type["Model"]:
        model = self.field.model
        if model is None:
            raise RuntimeError("Many-to-many field is not bound to a model.")
        return model

    def _related_pk_column(self, related_model: Type["Model"]) -> str:
        pk_field: Field | None = related_model._meta.primary_key
        if pk_field is None:
            return "id"
        return pk_field.column_name()

    def _normalize_targets(self, objs) -> list[Any]:
        related_model = self.field.model if self.is_reverse else self.field.remote_model
        if related_model is None:
            field_name = self.field.require_name()
            raise RuntimeError(f"Related model for field '{field_name}' is not resolved.")
        pks: list[Any] = []
        for obj in objs:
            if hasattr(obj, "pk"):
                pk_val = obj.pk
            else:
                pk_val = obj
            if pk_val is None:
                raise ValueError("Related instances must be saved before association.")
            pks.append(pk_val)
        return pks

    def all(self):
        session = self._session()
        related_model = self.field.model if self.is_reverse else self.field.remote_model
        if related_model is None:
            field_name = self.field.require_name()
            raise RuntimeError(f"Related model for field '{field_name}' is not resolved.")
        through_table = session.dialect.format_table(self._through_table())
        parent_col = self._right_column() if self.is_reverse else self._left_column()
        related_col = self._left_column() if self.is_reverse else self._right_column()
        parent_quoted = session.dialect.quote_identifier(parent_col)
        related_quoted = session.dialect.quote_identifier(related_col)
        junction_sql = f"SELECT {related_quoted} FROM {through_table} WHERE {parent_quoted} = {session.dialect.parameter_placeholder()}"
        cursor = session.execute(junction_sql, (self.instance.pk,))
        related_ids = [row[0] for row in cursor.fetchall()]
        if not related_ids:
            self.instance._related_cache[self.accessor_name] = []
            return []

        placeholders = ", ".join(session.dialect.parameter_placeholder() for _ in related_ids)
        table = session.dialect.format_table(related_model._meta.table_name)
        select_list = ", ".join(
            session.dialect.quote_identifier(f.column_name())
            for f in related_model._meta.get_fields()
        )
        pk_column = session.dialect.quote_identifier(self._related_pk_column(related_model))
        sql = f"SELECT {select_list} FROM {table} WHERE {pk_column} IN ({placeholders})"
        cursor = session.execute(sql, related_ids)
        rows = cursor.fetchall()
        results = []
        for row in rows:
            data = session._row_to_dict(cursor, row)
            results.append(session._materialize(related_model, data))
        self.instance._related_cache[self.accessor_name] = results
        return results

    def add(self, *objs) -> None:
        if self.instance.pk is None:
            raise ValueError("Instance must be saved before adding many-to-many relations.")
        session = self._session()
        related_model = self.field.remote_model
        if related_model is None:
            field_name = self.field.require_name()
            raise RuntimeError(f"Related model for field '{field_name}' is not resolved.")
        target_pks = self._normalize_targets(objs)
        if not target_pks:
            return
        # Avoid duplicate inserts by fetching existing rows.
        through = session.dialect.format_table(self._through_table())
        parent_col = self._right_column() if self.is_reverse else self._left_column()
        related_col = self._left_column() if self.is_reverse else self._right_column()
        left_col = session.dialect.quote_identifier(parent_col)
        right_col = session.dialect.quote_identifier(related_col)
        existing_cursor = session.execute(
            f"SELECT {right_col} FROM {through} WHERE {left_col} = {session.dialect.parameter_placeholder()}",
            (self.instance.pk,),
        )
        existing = {row[0] for row in existing_cursor.fetchall()}
        new_values = [pk for pk in target_pks if pk not in existing]
        if not new_values:
            return
        insert_sql = f"INSERT INTO {through} ({left_col}, {right_col}) VALUES " + ", ".join(
            f"({session.dialect.parameter_placeholder()}, {session.dialect.parameter_placeholder()})"
            for _ in new_values
        )
        params: list[Any] = []
        for pk in new_values:
            # Order matches left_col (parent) then right_col (related)
            params.extend([self.instance.pk, pk] if not self.is_reverse else [self.instance.pk, pk])
        session.execute(insert_sql, params)
        self.instance._related_cache.pop(self.accessor_name, None)

    def remove(self, *objs) -> None:
        if self.instance.pk is None:
            return
        session = self._session()
        target_pks = self._normalize_targets(objs)
        if not target_pks:
            return
        through = session.dialect.format_table(self._through_table())
        parent_col = self._right_column() if self.is_reverse else self._left_column()
        related_col = self._left_column() if self.is_reverse else self._right_column()
        left_col = session.dialect.quote_identifier(parent_col)
        right_col = session.dialect.quote_identifier(related_col)
        placeholders = ", ".join(session.dialect.parameter_placeholder() for _ in target_pks)
        sql = (
            f"DELETE FROM {through} WHERE {left_col} = {session.dialect.parameter_placeholder()} "
            f"AND {right_col} IN ({placeholders})"
        )
        session.execute(sql, [self.instance.pk, *target_pks])
        self.instance._related_cache.pop(self.accessor_name, None)

    def clear(self) -> None:
        if self.instance.pk is None:
            return
        session = self._session()
        through = session.dialect.format_table(self._through_table())
        parent_col = self._right_column() if self.is_reverse else self._left_column()
        left_col = session.dialect.quote_identifier(parent_col)
        sql = f"DELETE FROM {through} WHERE {left_col} = {session.dialect.parameter_placeholder()}"
        session.execute(sql, (self.instance.pk,))
        self.instance._related_cache[self.accessor_name] = []

    def __iter__(self):
        return iter(self.all())


class ManyToManyDescriptor:
    def __init__(
        self,
        field: "ManyToManyField",
        source_model: Optional[Type["Model"]] = None,
        accessor_name: Optional[str] = None,
    ) -> None:
        self.field = field
        resolved_source = source_model or field.model
        if resolved_source is None:
            raise RuntimeError("Many-to-many field is not bound to a model.")
        self.source_model: Type["Model"] = resolved_source
        resolved_accessor = accessor_name or field.name
        if resolved_accessor is None:
            raise RuntimeError("Many-to-many field accessor name is not set.")
        self.accessor_name: str = resolved_accessor

    def __get__(self, instance, owner):
        if instance is None:
            return self
        cache = getattr(instance, "_related_cache", {})
        if self.accessor_name in cache:
            return cache[self.accessor_name]
        return ManyToManyManager(self.field, instance, self.source_model, self.accessor_name)


class ManyToManyField(RelatedField):
    relation_type = "many-to-many"

    def __init__(
        self,
        to: Type["Model"] | str,
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

    def contribute_to_class(self, model: Type["Model"], name: str) -> None:
        self.name = name
        self.model = model
        setattr(model, name, ManyToManyDescriptor(self, accessor_name=name))
        model._meta.many_to_many.append(self)
        if self.db_table:
            model._meta.m2m_through_tables[name] = self.db_table

    def through_table(self, model: Type["Model"]) -> str:
        if self.db_table:
            return self.db_table
        return f"{model._meta.table_name}_{self.remote_table_name()}"

    def remote_table_name(self) -> str:
        remote = self.remote_model
        if remote is None:
            raise RuntimeError("Remote model not resolved for ManyToManyField.")
        return remote._meta.table_name

    def left_column(self, model: Type["Model"]) -> str:
        return f"{model._meta.table_name}_id"

    def right_column(self, model: Type["Model"]) -> str:
        return f"{self.remote_table_name()}_id"

    def remote_pk_column(self) -> str:
        remote = self.remote_model
        if remote is None or remote._meta.primary_key is None:
            return "id"
        pk_field: Field = remote._meta.primary_key
        return pk_field.column_name()


class RelatedAccessor:
    def __init__(self, source_model: Type["Model"], field: RelatedField) -> None:
        self.source_model = source_model
        self.field = field

    def __get__(self, instance, owner):
        return RelatedManager(self.source_model, self.field, instance)


class RelatedManager:
    """
    Provides a QuerySet filtered by a parent instance for reverse relations.
    """

    def __init__(self, source_model: Type["Model"], field: RelatedField, instance) -> None:
        self.model = source_model
        self.field = field
        self.instance = instance

    def all(self):
        qs = self.model.objects.all()
        if self.instance:
            field_name = self.field.require_name()
            return qs.filter(**{field_name: self.instance.pk})
        return qs

    def filter(self, **lookups):
        return self.all().filter(**lookups)


class RelationRegistry:
    def __init__(self) -> None:
        self.models: Dict[str, Type["Model"]] = {}
        self.pending_fields: List[Tuple[Type["Model"], RelatedField]] = []
        # Track many-to-many fields to support reverse lookups without installing descriptors.
        self.m2m_reverse: Dict[Type["Model"], List[Tuple[Type["Model"], "ManyToManyField"]]] = (
            defaultdict(list)
        )

    def register_model(self, model: Type["Model"]) -> None:
        label = self._label(model)
        self.models[label] = model
        self._resolve_pending()

    def register_field(self, model: Type["Model"], field: RelatedField) -> None:
        target = self._resolve_target(field.to)
        if target is None:
            self.pending_fields.append((model, field))
            return
        field.resolve_model(target)
        if isinstance(field, ManyToManyField):
            self.m2m_reverse[target].append((model, field))
        self._attach_reverse_accessor(model, field)

    def _resolve_pending(self) -> None:
        unresolved = []
        for model, field in self.pending_fields:
            target = self._resolve_target(field.to)
            if target is None:
                unresolved.append((model, field))
                continue
            field.resolve_model(target)
            if isinstance(field, ManyToManyField):
                self.m2m_reverse[target].append((model, field))
            self._attach_reverse_accessor(model, field)
        self.pending_fields = unresolved

    def _resolve_target(self, target: Type["Model"] | str) -> Optional[Type["Model"]]:
        if isinstance(target, type):
            return target
        label = target.split(".")[-1]
        return self.models.get(label)

    def _label(self, model: Type["Model"]) -> str:
        return model.__name__

    def _attach_reverse_accessor(self, model: Type["Model"], field: RelatedField) -> None:
        remote = field.remote_model
        if remote is None:
            return
        related_name = field.related_name or f"{model.__name__.lower()}_set"
        if hasattr(remote, related_name):
            return
        if isinstance(field, ManyToManyField):
            descriptor: ManyToManyDescriptor | RelatedAccessor = ManyToManyDescriptor(
                field, source_model=remote, accessor_name=related_name
            )
        else:
            descriptor = RelatedAccessor(model, field)
        setattr(remote, related_name, descriptor)


relation_registry = RelationRegistry()
