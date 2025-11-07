"""
Schema builder converting model metadata into DDL statements.
"""

from __future__ import annotations

from typing import Iterable, List

from ..core.model import Model
from ..dialects.base import Dialect


class SchemaBuilder:
    """
    Produces dialect-specific SQL for schema manipulation.
    """

    def __init__(self, dialect: Dialect) -> None:
        self.dialect = dialect

    def create_table_sql(self, model: type[Model]) -> str:
        columns_sql = self._render_columns(model)
        table_name = self.dialect.format_table(model._meta.table_name)
        column_list = ", ".join(columns_sql)
        return f"CREATE TABLE IF NOT EXISTS {table_name} ({column_list})"

    def drop_table_sql(self, model: type[Model]) -> str:
        table_name = self.dialect.format_table(model._meta.table_name)
        return f"DROP TABLE IF EXISTS {table_name}"

    def _render_columns(self, model: type[Model]) -> List[str]:
        pieces: List[str] = []
        for field in model._meta.get_fields():
            column_type = field.db_type
            if not column_type:
                raise ValueError(f"Field '{field.name}' missing db_type for schema generation.")
            column_name = field.db_column or field.name
            column_def = self.dialect.render_column_definition(
                column_name,
                column_type,
                nullable=field.nullable if not field.primary_key else False,
            )
            extras: List[str] = []
            if field.primary_key:
                extras.append("PRIMARY KEY")
            if field.unique and not field.primary_key:
                extras.append("UNIQUE")
            default_sql = self._default_clause(field)
            if default_sql:
                extras.append(default_sql)

            if extras:
                column_def = f"{column_def} {' '.join(extras)}"
            pieces.append(column_def)
        return pieces

    def _default_clause(self, field) -> str | None:
        if field.db_default is not None:
            return f"DEFAULT {field.db_default}"
        if field.default is None or callable(field.default):
            return None
        value = field.default
        if isinstance(value, str):
            return f"DEFAULT '{value}'"
        if isinstance(value, bool):
            return f"DEFAULT {1 if value else 0}"
        return f"DEFAULT {value}"
