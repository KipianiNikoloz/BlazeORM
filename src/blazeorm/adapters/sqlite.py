"""
SQLite database adapter implementation.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
import logging
from typing import Any, Iterable, Sequence

from ..dialects.sqlite import SQLiteDialect
from ..utils import get_logger, time_call
from .base import ConnectionConfig, DatabaseAdapter


@dataclass(slots=True)
class SQLiteConnectionState:
    connection: sqlite3.Connection


class SQLiteAdapter(DatabaseAdapter):
    """
    Adapter wrapping the Python stdlib sqlite3 module.
    """

    def __init__(self) -> None:
        self.dialect = SQLiteDialect()
        self._state: SQLiteConnectionState | None = None
        self.logger = get_logger("adapters.sqlite")

    # ------------------------------------------------------------------ #
    # Connection management
    # ------------------------------------------------------------------ #
    def connect(self, config: ConnectionConfig) -> sqlite3.Connection:
        path = self._normalize_path(config.url)
        timeout = config.timeout if config.timeout is not None else 5.0

        connection = sqlite3.connect(
            path,
            isolation_level=None if config.autocommit else "",
            timeout=timeout,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        if config.isolation_level:
            connection.isolation_level = config.isolation_level

        self._state = SQLiteConnectionState(connection)
        return connection

    def close(self) -> None:
        if self._state:
            self._state.connection.close()
            self._state = None

    def _ensure_connection(self) -> sqlite3.Connection:
        if not self._state:
            raise RuntimeError("SQLiteAdapter is not connected.")
        return self._state.connection

    # ------------------------------------------------------------------ #
    # Execution helpers
    # ------------------------------------------------------------------ #
    def execute(self, sql: str, params: Sequence[Any] | None = None) -> sqlite3.Cursor:
        connection = self._ensure_connection()
        cursor = connection.cursor()
        params = params or ()
        with time_call("sqlite.execute", self.logger):
            cursor.execute(sql, params)
        self.logger.debug("SQL executed", extra={"sql": sql, "params": self._redact(params)})
        return cursor

    def executemany(
        self, sql: str, seq_of_params: Sequence[Sequence[Any]] | Iterable[Sequence[Any]]
    ) -> sqlite3.Cursor:
        connection = self._ensure_connection()
        cursor = connection.cursor()
        with time_call("sqlite.executemany", self.logger):
            cursor.executemany(sql, seq_of_params)
        return cursor

    # ------------------------------------------------------------------ #
    # Transactions
    # ------------------------------------------------------------------ #
    def begin(self) -> None:
        connection = self._ensure_connection()
        connection.execute("BEGIN")

    def commit(self) -> None:
        connection = self._ensure_connection()
        connection.commit()

    def rollback(self) -> None:
        connection = self._ensure_connection()
        connection.rollback()

    # ------------------------------------------------------------------ #
    def last_insert_id(self, cursor: sqlite3.Cursor, table: str, pk_column: str) -> Any:
        return cursor.lastrowid

    @staticmethod
    def _normalize_path(url: str) -> str:
        if url == "sqlite:///:memory:":
            return ":memory:"
        prefix = "sqlite:///"
        if url.startswith(prefix):
            return url[len(prefix) :]
        return url

    @staticmethod
    def _redact(params: Sequence[Any]) -> Sequence[Any]:
        redacted = []
        for value in params:
            if isinstance(value, str) and "password" in value.lower():
                redacted.append("***")
            else:
                redacted.append(value)
        return redacted
