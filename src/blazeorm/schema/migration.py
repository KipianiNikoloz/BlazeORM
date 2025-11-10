"""
Simple migration engine executing DDL operations with version tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Sequence

from ..adapters.base import DatabaseAdapter
from ..dialects.base import Dialect
from ..security.migrations import confirm_destructive_operation
from ..utils import get_logger
from .builder import SchemaBuilder


@dataclass
class MigrationOperation:
    sql: str
    destructive: bool = False
    force: bool = False
    description: str | None = None


class MigrationEngine:
    """
    Executes migrations and records applied versions.
    """

    def __init__(
        self,
        adapter: DatabaseAdapter,
        dialect: Dialect,
        *,
        version_table: str = "blazeorm_migrations",
    ) -> None:
        self.adapter = adapter
        self.dialect = dialect
        self.builder = SchemaBuilder(dialect)
        self.version_table = version_table
        self.logger = get_logger("schema.migration")
        self._ensure_version_table()

    def _ensure_version_table(self) -> None:
        table = self.dialect.format_table(self.version_table)
        sql = (
            f"CREATE TABLE IF NOT EXISTS {table} ("
            '"app" TEXT NOT NULL, '
            '"name" TEXT NOT NULL, '
            '"applied_at" TEXT NOT NULL, '
            "PRIMARY KEY(app, name)"
            ")"
        )
        self.adapter.execute(sql)

    def applied_migrations(self) -> List[tuple[str, str]]:
        table = self.dialect.format_table(self.version_table)
        cursor = self.adapter.execute(f"SELECT app, name FROM {table} ORDER BY applied_at")
        return [(row["app"], row["name"]) for row in cursor.fetchall()]

    def apply(self, app: str, name: str, operations: Sequence[MigrationOperation]) -> None:
        with self._transaction():
            for op in operations:
                if op.destructive:
                    description = op.description or op.sql
                    self.logger.warning(
                        "Destructive migration detected: %s (force=%s)", description, op.force
                    )
                    confirm_destructive_operation(description, force=op.force)
                self.adapter.execute(op.sql)
            self._record_migration(app, name)

    def _transaction(self):
        from contextlib import contextmanager

        adapter = self.adapter

        @contextmanager
        def ctx():
            adapter.begin()
            try:
                yield
            except Exception:
                adapter.rollback()
                raise
            else:
                adapter.commit()

        return ctx()

    def _record_migration(self, app: str, name: str) -> None:
        table = self.dialect.format_table(self.version_table)
        timestamp = datetime.now(timezone.utc).isoformat()
        self.adapter.execute(
            f"INSERT INTO {table} (app, name, applied_at) VALUES (?, ?, ?)",
            (app, name, timestamp),
        )
