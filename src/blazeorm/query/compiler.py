"""
SQL compilation utilities translating expressions into SQL strings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Tuple

from ..core.relations import RelatedField
from ..dialects.base import Dialect
from .expressions import Q

if TYPE_CHECKING:
    from ..core.model import Model


LOOKUP_OPERATORS = {
    "exact": "=",
    "iexact": "LIKE",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "contains": "LIKE",
}


class SQLCompiler:
    """
    Compile QuerySet state into SQL statements and parameters.
    """

    def __init__(
        self,
        model: type["Model"],
        dialect: Dialect,
        where: Q | None = None,
        ordering: tuple[str, ...] = (),
        limit: int | None = None,
        offset: int | None = None,
        select_related: Tuple[str, ...] = (),
    ) -> None:
        self.model = model
        self.dialect = dialect
        self.where = where
        self.ordering = ordering
        self.limit = limit
        self.offset = offset
        self.select_related = select_related

    def compile(self) -> Tuple[str, List[Any]]:
        select_list = self._build_select_list()
        sql_parts: List[str] = [f"SELECT {select_list}", "FROM", self._table_for_model(self.model)]
        sql_parts.extend(self._build_select_related_joins())
        params: List[Any] = []

        if self.where and not self.where.is_empty():
            where_sql, where_params = self._compile_q(self.where)
            if where_sql:
                sql_parts.append("WHERE")
                sql_parts.append(where_sql)
                params.extend(where_params)

        if self.ordering:
            order_sql = ", ".join(self._compile_ordering(field) for field in self.ordering)
            sql_parts.append("ORDER BY")
            sql_parts.append(order_sql)

        limit_clause = self.dialect.limit_clause(self.limit, self.offset)
        if limit_clause:
            sql_parts.append(limit_clause)

        return " ".join(sql_parts), params

    # Helpers -----------------------------------------------------------
    def _table_for_model(self, model: type["Model"]) -> str:
        return self.dialect.format_table(model._meta.table_name)

    def _qualified(self, table: str, column: str) -> str:
        return f"{table}.{self.dialect.quote_identifier(column)}"

    def _build_select_list(self) -> str:
        columns: List[str] = []
        base_table = self._table_for_model(self.model)
        for field in self.model._meta.get_fields():
            columns.append(self._qualified(base_table, field.column_name()))

        for path in self.select_related:
            related_model = self._get_related_model(path)
            table = self._table_for_model(related_model)
            for field in related_model._meta.get_fields():
                alias = f"{path}__{field.require_name()}"
                columns.append(
                    f"{self._qualified(table, field.column_name())} AS {self.dialect.quote_identifier(alias)}"
                )
        return ", ".join(columns)

    def _build_select_related_joins(self) -> List[str]:
        joins: List[str] = []
        base_table = self._table_for_model(self.model)
        for path in self.select_related:
            field = self._get_relation_field(self.model, path)
            remote_model = field.remote_model
            if remote_model is None:
                raise ValueError(f"Relation '{path}' could not be resolved.")
            remote_table = self._table_for_model(remote_model)
            fk_column = field.column_name()
            pk_field = remote_model._meta.primary_key
            if pk_field is None:
                raise ValueError(f"Related model '{remote_model.__name__}' lacks primary key.")
            pk_column = pk_field.column_name()
            joins.append(
                f"LEFT JOIN {remote_table} ON {self._qualified(base_table, fk_column)} = {self._qualified(remote_table, pk_column)}"
            )
        return joins

    def _get_related_model(self, path: str):
        field = self._get_relation_field(self.model, path)
        if field.remote_model is None:
            raise ValueError(f"Relation '{path}' could not be resolved.")
        return field.remote_model

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
            if current_field.relation_type == "many-to-many":
                raise ValueError("select_related does not support many-to-many relationships.")
            if current_field.remote_model is None:
                raise ValueError(f"Relation target '{current_field.to}' is not resolved.")
            field = current_field
            current_model = current_field.remote_model
        if field is None:
            raise ValueError(f"Invalid relation path '{path}'")
        return field

    # Compilation helpers -----------------------------------------------
    def _compile_ordering(self, field_name: str) -> str:
        descending = field_name.startswith("-")
        name = field_name[1:] if descending else field_name
        field = self.model._meta.get_field(name)
        clause = self.dialect.quote_identifier(field.column_name())
        if descending:
            clause += " DESC"
        return clause

    def _compile_q(self, q: Q) -> Tuple[str, List[Any]]:
        if not q.children:
            return "", []

        parts: List[str] = []
        params: List[Any] = []

        for child in q.children:
            if isinstance(child, Q):
                child_sql, child_params = self._compile_q(child)
                if child_sql:
                    parts.append(f"({child_sql})")
                    params.extend(child_params)
            elif isinstance(child, tuple):
                field_lookup, value = child
                sql, child_params = self._compile_lookup(field_lookup, value)
                parts.append(sql)
                params.extend(child_params)

        if not parts:
            return "", []

        separator = f" {q.connector} "
        sql = separator.join(parts)
        if q.negated:
            sql = f"NOT ({sql})"
        return sql, params

    def _compile_lookup(self, field_lookup: str, value: Any) -> Tuple[str, List[Any]]:
        if "__" in field_lookup:
            field_name, lookup = field_lookup.split("__", 1)
        else:
            field_name, lookup = field_lookup, "exact"

        field = self.model._meta.get_field(field_name)
        column = self.dialect.quote_identifier(field.column_name())

        if value is None:
            if lookup != "exact":
                raise ValueError("NULL comparison only supported for equality.")
            return f"{column} IS NULL", []

        operator = LOOKUP_OPERATORS.get(lookup)
        if operator is None:
            raise ValueError(f"Unsupported lookup '{lookup}'")

        placeholder = self.dialect.parameter_placeholder()
        if lookup == "contains":
            value = f"%{value}%"
        if lookup == "iexact":
            value = value.lower()

        return f"{column} {operator} {placeholder}", [value]
