"""
QuerySet implementation providing a chainable query API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Optional, Tuple

from ..core.relations import ManyToManyField, RelatedField, relation_registry
from ..dialects.sqlite import SQLiteDialect
from .compiler import SQLCompiler
from .expressions import Q

if TYPE_CHECKING:
    from ..core.model import Model
    from ..persistence.session import Session


class QuerySet:
    """
    Lightweight QuerySet capable of compiling to SQL strings.
    Execution will be delegated to persistence layer in later milestones.
    """

    def __init__(
        self,
        model: type["Model"],
        *,
        dialect=None,
        where: Optional[Q] = None,
        ordering: Tuple[str, ...] = (),
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        select_related: Tuple[str, ...] = (),
        prefetch_related: Tuple[str, ...] = (),
        session: "Session | None" = None,
    ) -> None:
        self.model = model
        self.dialect = dialect or SQLiteDialect()
        self._where = where or Q()
        self._ordering = ordering
        self._limit = limit
        self._offset = offset
        self._select_related = select_related
        self._prefetch_related = prefetch_related
        self._session = session

    # Public API --------------------------------------------------------
    def filter(self, **lookups: Any) -> "QuerySet":
        return self._clone(where=self._add_q(Q(**lookups)))

    def exclude(self, **lookups: Any) -> "QuerySet":
        return self._clone(where=self._add_q(~Q(**lookups)))

    def where(self, q_object: Q) -> "QuerySet":
        return self._clone(where=self._add_q(q_object))

    def order_by(self, *fields: str) -> "QuerySet":
        return self._clone(ordering=tuple(fields))

    def limit(self, value: int) -> "QuerySet":
        return self._clone(limit=value)

    def offset(self, value: int) -> "QuerySet":
        return self._clone(offset=value)

    def select_related(self, *fields: str) -> "QuerySet":
        if not fields:
            raise ValueError("select_related() requires at least one relationship name.")
        combined = tuple(dict.fromkeys(self._select_related + fields))
        return self._clone(select_related=combined)

    def prefetch_related(self, *fields: str) -> "QuerySet":
        if not fields:
            raise ValueError("prefetch_related() requires at least one relationship name.")
        combined = tuple(dict.fromkeys(self._prefetch_related + fields))
        return self._clone(prefetch_related=combined)

    def to_sql(self) -> tuple[str, list[Any]]:
        compiler = SQLCompiler(
            model=self.model,
            dialect=self.dialect,
            where=self._where,
            ordering=self._ordering,
            limit=self._limit,
            offset=self._offset,
            select_related=self._select_related,
        )
        return compiler.compile()

    # Iteration placeholder (will integrate with persistence later)
    def __iter__(self) -> Iterable["Model"]:
        session = self._session
        if session is None:
            from ..persistence.session import Session as SessionCls

            session = SessionCls.current()
        if session is None:
            raise RuntimeError(
                "QuerySet iteration requires a bound Session. Use Session.query(model) or iterate within an active Session context."
            )
        sql, params = self.to_sql()
        cursor = session.execute(sql, params)
        rows = cursor.fetchall()
        instances = []
        for row in rows:
            data = self._row_to_dict(cursor, row)
            base_data, related_chunks = self._split_related_data(data)
            instance = session._materialize(self.model, base_data)
            if self._select_related:
                self._hydrate_select_related(session, instance, related_chunks)
            instances.append(instance)
        if self._prefetch_related:
            self._prefetch_related_data(session, instances)
        return iter(instances)

    # Internal helpers --------------------------------------------------
    def _add_q(self, q_object: Q) -> Q:
        if self._where.is_empty():
            return q_object
        return self._where & q_object

    def _clone(self, **overrides: Any) -> "QuerySet":
        params = {
            "model": self.model,
            "dialect": self.dialect,
            "where": overrides.get("where", self._where),
            "ordering": overrides.get("ordering", self._ordering),
            "limit": overrides.get("limit", self._limit),
            "offset": overrides.get("offset", self._offset),
            "select_related": overrides.get("select_related", self._select_related),
            "prefetch_related": overrides.get("prefetch_related", self._prefetch_related),
            "session": overrides.get("session", self._session),
        }
        return QuerySet(**params)

    @staticmethod
    def _row_to_dict(cursor, row) -> dict[str, Any]:
        if hasattr(row, "keys"):
            return dict(row)
        if hasattr(cursor, "description"):
            columns = [col[0] for col in cursor.description]
            return {col: row[idx] for idx, col in enumerate(columns)}
        raise ValueError("Unable to map database row to dictionary.")

    def _split_related_data(
        self, data: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        base_data: dict[str, Any] = {}
        related_chunks: dict[str, dict[str, Any]] = {}
        base_columns = {
            field.db_column or field.name: field.name for field in self.model._meta.get_fields()
        }
        for key, value in data.items():
            if key in base_columns:
                base_data[base_columns[key]] = value
            elif "__" in key:
                path, column = key.split("__", 1)
                related_chunks.setdefault(path, {})[column] = value
        return base_data, related_chunks

    def _hydrate_select_related(
        self,
        session: "Session",
        instance: "Model",
        related_chunks: dict[str, dict[str, Any]],
    ) -> None:
        for path in self._select_related:
            field = self._get_relation_field(self.model, path)
            related_model = field.remote_model
            if related_model is None:
                continue
            related_data = related_chunks.get(path)
            if not related_data:
                setattr(instance, field.name, None)
                continue
            pk_field = related_model._meta.primary_key
            if pk_field and related_data.get(pk_field.name) is None:
                setattr(instance, field.name, None)
                continue
            related_instance = session._materialize(related_model, related_data)
            setattr(instance, field.name, related_instance)

    def _prefetch_related_data(self, session: "Session", instances: list["Model"]) -> None:
        if not instances:
            return
        for relation in self._prefetch_related:
            if "__" in relation:
                head, tail = relation.split("__", 1)
                self._prefetch_relation(session, instances, head)
                children: list[Any] = []
                for obj in instances:
                    value = getattr(obj, head, None)
                    if value is None:
                        continue
                    if isinstance(value, list):
                        children.extend(value)
                    else:
                        children.append(value)
                if children:
                    child_model = children[0].__class__
                    QuerySet(
                        child_model, session=session, prefetch_related=(tail,)
                    )._prefetch_related_data(session, children)
                continue
            self._prefetch_relation(session, instances, relation)

    def _prefetch_relation(
        self, session: "Session", instances: list["Model"], relation: str
    ) -> None:
        # Forward relation on the model
        if self._is_forward_relation(self.model, relation):
            try:
                field = self.model._meta.get_field(relation)
            except KeyError:
                field = self._get_m2m_field(self.model, relation)
            if isinstance(field, ManyToManyField):
                related_model = field.remote_model
                current_model = self.model
                if related_model is None:
                    return
                # If field is declared on a different model (reverse via related_name),
                # treat related_model as the declaring model for hydration.
                if related_model is current_model:
                    related_model = field.model
                self._prefetch_many_to_many(
                    session, instances, related_model, field, relation, current_model=current_model
                )
                return
            self._prefetch_forward(session, instances, relation)
            return
        # Reverse relation via related_name
        target = self._find_reverse_relation(self.model, relation)
        if target is None:
            raise ValueError(
                f"Cannot prefetch relation '{relation}' for model '{self.model.__name__}'"
            )
        related_model, field = target
        if isinstance(field, ManyToManyField):
            self._prefetch_many_to_many(session, instances, related_model, field, relation)
            return
        pk_field = self.model._meta.primary_key
        if pk_field is None:
            return
        parent_pks = [
            getattr(obj, pk_field.name)
            for obj in instances
            if getattr(obj, pk_field.name) is not None
        ]
        if not parent_pks:
            return
        placeholders = ", ".join(session.dialect.parameter_placeholder() for _ in parent_pks)
        table = session.dialect.format_table(related_model._meta.table_name)
        fk_column = session.dialect.quote_identifier(field.db_column or field.name)
        select_list = ", ".join(
            session.dialect.quote_identifier(f.db_column or f.name)
            for f in related_model._meta.get_fields()
        )
        sql = f"SELECT {select_list} FROM {table} WHERE {fk_column} IN ({placeholders})"
        cursor = session.execute(sql, parent_pks)
        rows = cursor.fetchall()
        bucket: dict[Any, list[Any]] = {pk: [] for pk in parent_pks}
        for row in rows:
            row_data = self._row_to_dict(cursor, row)
            child = session._materialize(related_model, row_data)
            parent_key = row_data.get(field.db_column or field.name)
            bucket.setdefault(parent_key, []).append(child)
        for obj in instances:
            parent_pk = getattr(obj, pk_field.name)
            setattr(obj, relation, bucket.get(parent_pk, []))

    def _prefetch_forward(
        self, session: "Session", instances: list["Model"], relation: str
    ) -> None:
        field = self.model._meta.get_field(relation)
        if not isinstance(field, RelatedField):
            return
        remote_model = field.remote_model
        if remote_model is None:
            return
        fk_values = []
        for obj in instances:
            val = getattr(obj, field.name)
            if hasattr(val, "pk"):
                val = val.pk
            if val is not None:
                fk_values.append(val)
        if not fk_values:
            return
        placeholders = ", ".join(session.dialect.parameter_placeholder() for _ in fk_values)
        table = session.dialect.format_table(remote_model._meta.table_name)
        pk_field = remote_model._meta.primary_key
        pk_column = (
            session.dialect.quote_identifier(pk_field.db_column or pk_field.name)
            if pk_field
            else session.dialect.quote_identifier("id")
        )
        select_list = ", ".join(
            session.dialect.quote_identifier(f.db_column or f.name)
            for f in remote_model._meta.get_fields()
        )
        sql = f"SELECT {select_list} FROM {table} WHERE {pk_column} IN ({placeholders})"
        cursor = session.execute(sql, fk_values)
        rows = cursor.fetchall()
        related_map: dict[Any, Any] = {}
        for row in rows:
            row_data = self._row_to_dict(cursor, row)
            related_instance = session._materialize(remote_model, row_data)
            if pk_field is not None:
                related_map[row_data.get(pk_field.name)] = related_instance
        for obj in instances:
            fk_val = getattr(obj, field.name)
            if hasattr(fk_val, "pk"):
                fk_val = fk_val.pk
            setattr(obj, relation, related_map.get(fk_val))

    def _prefetch_many_to_many(
        self,
        session: "Session",
        instances: list["Model"],
        related_model: type["Model"],
        field: "ManyToManyField",
        relation: str,
        current_model: type["Model"],
    ) -> None:
        pk_field = current_model._meta.primary_key
        if pk_field is None:
            return
        parent_pks = [
            getattr(obj, pk_field.name)
            for obj in instances
            if getattr(obj, pk_field.name) is not None
        ]
        if not parent_pks:
            return
        through = session.dialect.format_table(field.through_table(field.model))
        parent_is_remote = current_model is field.remote_model
        parent_col_raw = (
            field.right_column(field.model) if parent_is_remote else field.left_column(field.model)
        )
        related_col_raw = (
            field.left_column(field.model) if parent_is_remote else field.right_column(field.model)
        )
        parent_col = session.dialect.quote_identifier(parent_col_raw)
        related_col = session.dialect.quote_identifier(related_col_raw)
        placeholders = ", ".join(session.dialect.parameter_placeholder() for _ in parent_pks)
        junction_sql = f"SELECT {parent_col} AS parent_id, {related_col} AS related_id FROM {through} WHERE {parent_col} IN ({placeholders})"
        cursor = session.execute(junction_sql, parent_pks)
        rows = cursor.fetchall()
        if not rows:
            for obj in instances:
                obj._related_cache[relation] = []
            return
        related_ids = [row["related_id"] if hasattr(row, "keys") else row[1] for row in rows]
        unique_related_ids = list(dict.fromkeys(related_ids))
        placeholders_rel = ", ".join(
            session.dialect.parameter_placeholder() for _ in unique_related_ids
        )
        table = session.dialect.format_table(related_model._meta.table_name)
        select_list = ", ".join(
            session.dialect.quote_identifier(f.db_column or f.name)
            for f in related_model._meta.get_fields()
        )
        related_pk_field = related_model._meta.primary_key
        related_pk_column = (
            related_pk_field.db_column or related_pk_field.name if related_pk_field else "id"
        )
        related_cursor = session.execute(
            f"SELECT {select_list} FROM {table} WHERE {session.dialect.quote_identifier(related_pk_column)} IN ({placeholders_rel})",
            unique_related_ids,
        )
        related_rows = related_cursor.fetchall()
        related_map: dict[Any, Any] = {}
        for row in related_rows:
            data = self._row_to_dict(related_cursor, row)
            instance = session._materialize(related_model, data)
            pk_val = data.get(related_pk_column)
            related_map[pk_val] = instance

        bucket: dict[Any, list[Any]] = {pk: [] for pk in parent_pks}
        for row in rows:
            parent_id = row["parent_id"] if hasattr(row, "keys") else row[0]
            related_id = row["related_id"] if hasattr(row, "keys") else row[1]
            bucket.setdefault(parent_id, []).append(related_map.get(related_id))

        for obj in instances:
            parent_pk = getattr(obj, pk_field.name)
            obj._related_cache[relation] = [
                rel for rel in bucket.get(parent_pk, []) if rel is not None
            ]

    def _is_forward_relation(self, model: type["Model"], name: str) -> bool:
        try:
            field = model._meta.get_field(name)
        except KeyError:
            return self._get_m2m_field(model, name) is not None
        return isinstance(field, RelatedField)

    def _get_m2m_field(self, model: type["Model"], name: str):
        for field in model._meta.many_to_many:
            if field.name == name:
                return field
        # Check reverse registry for related_name pointing back to this model
        for candidate, field in relation_registry.m2m_reverse.get(model, []):
            if (field.related_name or f"{candidate.__name__.lower()}_set") == name:
                return field
        return None

    def _find_reverse_relation(self, model: type["Model"], related_name: str):
        # Prefer the related accessor/manager on the model if present
        accessor = getattr(model, related_name, None)
        from ..core.relations import RelatedField, RelatedManager

        if isinstance(accessor, RelatedManager) and isinstance(accessor.field, RelatedField):
            if accessor.field.remote_model is model:
                return accessor.model, accessor.field

        # Check many-to-many reverse map
        for candidate, field in relation_registry.m2m_reverse.get(model, []):
            if (field.related_name or f"{candidate.__name__.lower()}_set") == related_name:
                return candidate, field

        # Fallback: scan registry for non-M2M relations
        for candidate in relation_registry.models.values():
            for field in candidate._meta.get_fields():
                if not isinstance(field, RelatedField):
                    continue
                if (
                    field.remote_model is model
                    and (field.related_name or f"{candidate.__name__.lower()}_set") == related_name
                ):
                    return candidate, field
        return None

    def _get_relation_field(self, model: type["Model"], path: str) -> RelatedField:
        segments = path.split("__")
        current_model = model
        field: RelatedField | None = None
        for segment in segments:
            current_field = current_model._meta.get_field(segment)
            if not isinstance(current_field, RelatedField):
                raise ValueError(
                    f"Field '{segment}' on '{current_model.__name__}' is not a relationship."
                )
            if current_field.remote_model is None:
                raise ValueError(f"Relation target '{current_field.to}' is not resolved.")
            field = current_field
            current_model = current_field.remote_model
        if field is None:
            raise ValueError(f"Invalid relation path '{path}'")
        return field


class QueryManager:
    """
    Default manager for models providing QuerySet access.
    """

    def __init__(self, model: type["Model"]) -> None:
        self.model = model

    def all(self) -> QuerySet:
        return QuerySet(self.model)

    def filter(self, **lookups: Any) -> QuerySet:
        return self.all().filter(**lookups)

    def exclude(self, **lookups: Any) -> QuerySet:
        return self.all().exclude(**lookups)

    def where(self, q_object: Q) -> QuerySet:
        return self.all().where(q_object)

    def select_related(self, *fields: str) -> QuerySet:
        return self.all().select_related(*fields)

    def prefetch_related(self, *fields: str) -> QuerySet:
        return self.all().prefetch_related(*fields)

    def order_by(self, *fields: str) -> QuerySet:
        return self.all().order_by(*fields)
# mypy: ignore-errors
