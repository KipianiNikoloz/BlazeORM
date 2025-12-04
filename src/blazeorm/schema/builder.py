"""
Schema builder converting model metadata into DDL statements.
"""

from __future__ import annotations

from typing import Iterable, List

from ..core.model import Model
from ..dialects.base import Dialect
from ..utils import get_logger


class SchemaBuilder:
    """
    Produces dialect-specific SQL for schema manipulation.
    """

    def __init__(self, dialect: Dialect) -> None:
        self.dialect = dialect
        self.logger = get_logger("schema.builder")

    def create_table_sql(self, model: type[Model]) -> str:
        columns_sql = self._render_columns(model)
        table_name = self.dialect.format_table(model._meta.table_name)
        column_list = ", ".join(columns_sql)
        return f"CREATE TABLE IF NOT EXISTS {table_name} ({column_list})"

    def create_many_to_many_sql(self, model: type[Model]) -> list[str]:
        stmts: list[str] = []
        for field in dict.fromkeys(model._meta.many_to_many):
            through_table = self.dialect.format_table(field.through_table(model))
            left_col = self.dialect.quote_identifier(field.left_column(model))
            right_col = self.dialect.quote_identifier(field.right_column(model))
            remote = field.remote_model
            if remote is None:
                continue
            remote_table = self.dialect.format_table(remote._meta.table_name)
            remote_pk = field.remote_pk_column()
            pk_col = self.dialect.quote_identifier(remote_pk)
            stmt = (
                f"CREATE TABLE IF NOT EXISTS {through_table} ("
                f"{left_col} INTEGER NOT NULL, "
                f"{right_col} INTEGER NOT NULL, "
                f"UNIQUE ({left_col}, {right_col})"
                ")"
            )
            stmts.append(stmt)
        return stmts

    def drop_table_sql(self, model: type[Model]) -> str:
        table_name = self.dialect.format_table(model._meta.table_name)
        self.logger.warning(
            "DROP TABLE generated for %s; confirm destructive migration before applying.",
            table_name,
        )
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
