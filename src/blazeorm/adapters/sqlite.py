"""
SQLite database adapter implementation.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Sequence, cast

from ..dialects.sqlite import SQLiteDialect
from ..security.redaction import redact_params
from ..utils import get_logger, time_call
from ..utils.performance import resolve_slow_query_ms
from .base import (
    AdapterConnectionError,
    AdapterExecutionError,
    ConnectionConfig,
    Cursor,
    DatabaseAdapter,
)


@dataclass
class SQLiteConnectionState:
    connection: sqlite3.Connection
    config: ConnectionConfig


class SQLiteAdapter(DatabaseAdapter):
    """
    Adapter wrapping the Python stdlib sqlite3 module.
    """

    def __init__(self, slow_query_ms: int | None = None) -> None:
        self.dialect = SQLiteDialect()
        self._state: SQLiteConnectionState | None = None
        self.logger = get_logger("adapters.sqlite")
        self.slow_query_ms = resolve_slow_query_ms(default=100, override=slow_query_ms)

    # ------------------------------------------------------------------ #
    # Connection management
    # ------------------------------------------------------------------ #
    def connect(self, config: ConnectionConfig) -> sqlite3.Connection:
        path = self._normalize_path(config.url)
        timeout = config.timeout if config.timeout is not None else 5.0
        self.logger.info(
            "Connecting to SQLite database %s (autocommit=%s)",
            config.descriptive_label(),
            config.autocommit,
        )

        try:
            connection = sqlite3.connect(
                path,
                isolation_level=None if config.autocommit else "DEFERRED",
                timeout=timeout,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False,
            )
        except Exception as exc:
            raise AdapterConnectionError("Failed to connect to SQLite.") from exc
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        if config.isolation_level:
            # sqlite3 types expect specific literals; allow override and silence typing complaints.
            connection.isolation_level = config.isolation_level  # type: ignore[assignment]

        self._state = SQLiteConnectionState(connection, config)
        return connection

    def close(self) -> None:
        if self._state:
            try:
                self._state.connection.close()
            finally:
                self._state = None

    def _ensure_connection(self) -> sqlite3.Connection:
        if not self._state:
            raise AdapterConnectionError("SQLiteAdapter is not connected.")
        return self._state.connection

    # ------------------------------------------------------------------ #
    # Execution helpers
    # ------------------------------------------------------------------ #
    def execute(self, sql: str, params: Sequence[Any] | None = None) -> Cursor:
        connection = self._ensure_connection()
        cursor = cast(Cursor, connection.cursor())
        params = params or ()
        self._validate_params(sql, params)
        with time_call(
            "sqlite.execute",
            self.logger,
            sql=sql,
            params=self._redact(params),
            threshold_ms=self.slow_query_ms,
        ):
            cursor.execute(sql, params)
        return cursor

    def executemany(
        self, sql: str, seq_of_params: Sequence[Sequence[Any]] | Iterable[Sequence[Any]]
    ) -> Cursor:
        connection = self._ensure_connection()
        cursor = cast(Cursor, connection.cursor())
        seq = list(seq_of_params)
        for params in seq:
            self._validate_params(sql, params)
        with time_call(
            "sqlite.executemany",
            self.logger,
            sql=sql,
            params="bulk",
            threshold_ms=self.slow_query_ms,
        ):
            cursor.executemany(sql, seq)
        return cursor

    # ------------------------------------------------------------------ #
    # Transactions
    # ------------------------------------------------------------------ #
    def begin(self) -> None:
        connection = self._ensure_connection()
        if hasattr(connection, "in_transaction") and connection.in_transaction:
            return
        connection.execute("BEGIN")

    def commit(self) -> None:
        connection = self._ensure_connection()
        connection.commit()

    def rollback(self) -> None:
        connection = self._ensure_connection()
        connection.rollback()

    # ------------------------------------------------------------------ #
    def last_insert_id(self, cursor: Cursor, table: str, pk_column: str) -> Any:
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
        return redact_params(params)

    @staticmethod
    def _count_placeholders(sql: str) -> int:
        return sql.count("?")

    def _validate_params(self, sql: str, params: Sequence[Any]) -> None:
        placeholder_count = self._count_placeholders(sql)
        if not params:
            return
        if placeholder_count == 0:
            raise AdapterExecutionError(
                "Parameters provided but SQL statement has no placeholders."
            )
        if placeholder_count != len(params):
            raise AdapterExecutionError(
                f"Parameter count mismatch: expected {placeholder_count}, received {len(params)}."
            )
