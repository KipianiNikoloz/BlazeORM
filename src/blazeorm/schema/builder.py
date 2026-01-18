"""
Schema builder converting model metadata into DDL statements.
"""

from __future__ import annotations

from typing import List

from ..core.model import Model
from ..core.relations import ManyToManyField, RelatedField
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
            pieces: list[str] = [
                f"{left_col} INTEGER NOT NULL",
                f"{right_col} INTEGER NOT NULL",
                f"UNIQUE ({left_col}, {right_col})",
            ]
            pieces.extend(self._render_m2m_foreign_keys(model, field, left_col, right_col))
            stmt = f"CREATE TABLE IF NOT EXISTS {through_table} ({', '.join(pieces)})"
            stmts.append(stmt)
        return stmts

    def create_index_sql(self, model: type[Model]) -> list[str]:
        stmts: list[str] = []
        table_name = self.dialect.format_table(model._meta.table_name)
        for field in model._meta.get_fields():
            if not field.index or field.primary_key or field.unique:
                continue
            index_name = self._index_name(model, field)
            column = self.dialect.quote_identifier(field.column_name())
            index_ident = self.dialect.quote_identifier(index_name)
            if self.dialect.name == "mysql":
                stmt = f"CREATE INDEX {index_ident} ON {table_name} ({column})"
            else:
                stmt = f"CREATE INDEX IF NOT EXISTS {index_ident} ON {table_name} ({column})"
            stmts.append(stmt)
        return stmts

    def drop_table_sql(self, model: type[Model]) -> str:
        table_name = self.dialect.format_table(model._meta.table_name)
        self.logger.warning(
            "DROP TABLE generated for %s; confirm destructive migration before applying.",
            table_name,
        )
        return f"DROP TABLE IF EXISTS {table_name}"

    def drop_index_sql(self, model: type[Model]) -> list[str]:
        stmts: list[str] = []
        table_name = self.dialect.format_table(model._meta.table_name)
        for field in model._meta.get_fields():
            if not field.index or field.primary_key or field.unique:
                continue
            index_name = self._index_name(model, field)
            index_ident = self.dialect.quote_identifier(index_name)
            self.logger.warning(
                "DROP INDEX generated for %s; confirm destructive migration before applying.",
                index_name,
            )
            if self.dialect.name == "mysql":
                stmt = f"DROP INDEX {index_ident} ON {table_name}"
            else:
                stmt = f"DROP INDEX IF EXISTS {index_ident}"
            stmts.append(stmt)
        return stmts

    def _render_columns(self, model: type[Model]) -> List[str]:
        pieces: List[str] = []
        for field in model._meta.get_fields():
            column_type = field.db_type
            if not column_type:
                field_name = field.require_name()
                raise ValueError(f"Field '{field_name}' missing db_type for schema generation.")
            column_name = field.column_name()
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
        pieces.extend(self._render_foreign_keys(model))
        return pieces

    def _render_foreign_keys(self, model: type[Model]) -> list[str]:
        pieces: list[str] = []
        for field in model._meta.get_fields():
            if not isinstance(field, RelatedField) or isinstance(field, ManyToManyField):
                continue
            remote = field.remote_model
            if remote is None:
                raise ValueError(f"Relation target '{field.to}' is not resolved.")
            remote_pk = remote._meta.primary_key
            if remote_pk is None:
                raise ValueError(f"Related model '{remote.__name__}' lacks primary key.")
            local_col = self.dialect.quote_identifier(field.column_name())
            remote_table = self.dialect.format_table(remote._meta.table_name)
            remote_col = self.dialect.quote_identifier(remote_pk.column_name())
            pieces.append(
                self._foreign_key_clause(
                    local_col, remote_table, remote_col, on_delete=field.on_delete
                )
            )
        return pieces

    def _render_m2m_foreign_keys(
        self,
        model: type[Model],
        field: ManyToManyField,
        left_col: str,
        right_col: str,
    ) -> list[str]:
        local_pk = model._meta.primary_key
        remote = field.remote_model
        if local_pk is None or remote is None or remote._meta.primary_key is None:
            return []
        local_table = self.dialect.format_table(model._meta.table_name)
        remote_table = self.dialect.format_table(remote._meta.table_name)
        local_ref = self.dialect.quote_identifier(local_pk.column_name())
        remote_ref = self.dialect.quote_identifier(remote._meta.primary_key.column_name())
        return [
            self._foreign_key_clause(left_col, local_table, local_ref, on_delete=field.on_delete),
            self._foreign_key_clause(
                right_col, remote_table, remote_ref, on_delete=field.on_delete
            ),
        ]

    @staticmethod
    def _foreign_key_clause(
        local_col: str, remote_table: str, remote_col: str, *, on_delete: str | None
    ) -> str:
        clause = f"FOREIGN KEY ({local_col}) REFERENCES {remote_table} ({remote_col})"
        if on_delete:
            clause += f" ON DELETE {on_delete}"
        return clause

    @staticmethod
    def _index_name(model: type[Model], field) -> str:
        table_name = model._meta.table_name.replace(".", "_")
        column_name = field.column_name().replace(".", "_")
        return f"idx_{table_name}_{column_name}"

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
