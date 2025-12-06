"""
Dialect strategy interfaces describing SQL compilation behaviors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DialectCapabilities:
    """
    Feature flags describing backend capabilities.
    """

    supports_returning: bool = False
    supports_savepoints: bool = True
    supports_partial_indexes: bool = False
    supports_schema_namespaces: bool = False


class Dialect(Protocol):
    """
    Strategy interface consumed across query, schema, and adapter layers.
    """

    @property
    def name(self) -> str: ...

    @property
    def param_style(self) -> str: ...

    @property
    def capabilities(self) -> DialectCapabilities: ...

    def quote_identifier(self, identifier: str) -> str: ...

    def format_table(self, table_name: str) -> str: ...

    def limit_clause(self, limit: int | None, offset: int | None) -> str: ...

    def parameter_placeholder(self, position: int | None = None) -> str: ...

    def render_column_definition(self, column: str, column_type: str, *, nullable: bool) -> str: ...
