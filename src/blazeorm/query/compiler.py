"""
SQL compilation utilities translating expressions into SQL strings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Tuple

from ..dialects.base import Dialect
from .expressions import AND, OR, Q

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
    ) -> None:
        self.model = model
        self.dialect = dialect
        self.where = where
        self.ordering = ordering
        self.limit = limit
        self.offset = offset

    def compile(self) -> Tuple[str, List[Any]]:
        select_list = ", ".join(
            self.dialect.quote_identifier(field.db_column or field.name)
            for field in self.model._meta.get_fields()
        )
        sql_parts = [f"SELECT {select_list}", "FROM", self.dialect.format_table(self.model._meta.table_name)]
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

    # Compilation helpers -----------------------------------------------
    def _compile_ordering(self, field_name: str) -> str:
        descending = field_name.startswith("-")
        name = field_name[1:] if descending else field_name
        field = self.model._meta.get_field(name)
        clause = self.dialect.quote_identifier(field.db_column or field.name)
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
        column = self.dialect.quote_identifier(field.db_column or field.name)

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
