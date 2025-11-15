"""
MySQL dialect implementation.
"""

from __future__ import annotations

from typing import Final

from .base import Dialect, DialectCapabilities


class MySQLDialect:
    """
    MySQL dialect using percent-style placeholders.
    """

    name: Final[str] = "mysql"
    param_style: Final[str] = "pyformat"
    capabilities: Final[DialectCapabilities] = DialectCapabilities(
        supports_returning=False,
        supports_savepoints=True,
        supports_partial_indexes=False,
        supports_schema_namespaces=True,
    )

    def quote_identifier(self, identifier: str) -> str:
        escaped = identifier.replace("`", "``")
        return f"`{escaped}`"

    def format_table(self, table_name: str) -> str:
        if "." in table_name:
            schema, table = table_name.split(".", 1)
            return f"{self.quote_identifier(schema)}.{self.quote_identifier(table)}"
        return self.quote_identifier(table_name)

    def limit_clause(self, limit: int | None, offset: int | None) -> str:
        parts: list[str] = []
        if limit is not None:
            parts.append(f"LIMIT {limit}")
        if offset is not None:
            if limit is None:
                parts.append("LIMIT 18446744073709551615")
            parts.append(f"OFFSET {offset}")
        return " ".join(parts)

    def parameter_placeholder(self, position: int | None = None) -> str:
        return "%s"

    def render_column_definition(self, column: str, column_type: str, *, nullable: bool) -> str:
        null_clause = "" if nullable else " NOT NULL"
        return f"{self.quote_identifier(column)} {column_type}{null_clause}"


def get_mysql_dialect() -> Dialect:
    return MySQLDialect()
