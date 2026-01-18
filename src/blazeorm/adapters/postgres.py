"""
PostgreSQL database adapter implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from ..dialects.postgres import PostgresDialect
from ..utils import get_logger, time_call
from ..utils.performance import resolve_slow_query_ms
from .base import (
    AdapterConfigurationError,
    AdapterConnectionError,
    AdapterExecutionError,
    ConnectionConfig,
    DatabaseAdapter,
)


def _load_driver():
    try:
        import psycopg

        return psycopg
    except ImportError:
        return None


@dataclass
class PostgresConnectionState:
    connection: Any
    config: ConnectionConfig
    driver: Any


class PostgresAdapter(DatabaseAdapter):
    """
    Adapter wrapping the psycopg PostgreSQL driver.
    """

    def __init__(self, slow_query_ms: int | None = None) -> None:
        self.dialect = PostgresDialect()
        self._state: PostgresConnectionState | None = None
        self.logger = get_logger("adapters.postgres")
        self.slow_query_ms = resolve_slow_query_ms(default=100, override=slow_query_ms)

    def connect(self, config: ConnectionConfig) -> Any:
        driver = _load_driver()
        if driver is None:
            raise AdapterConfigurationError("psycopg is required to use PostgresAdapter.")

        options = dict(config.options or {})
        if config.ssl:
            for key, value in config.ssl.postgres_options().items():
                options.setdefault(key, value)
        if config.timeout and "connect_timeout" not in options:
            options["connect_timeout"] = int(config.timeout)

        self.logger.info(
            "Connecting to PostgreSQL %s (autocommit=%s)",
            config.descriptive_label(),
            config.autocommit,
        )

        try:
            connection = driver.connect(config.url, **options)
        except Exception as exc:
            raise AdapterConnectionError("Failed to connect to PostgreSQL.") from exc
        connection.autocommit = bool(config.autocommit)
        if config.isolation_level:
            setattr(connection, "isolation_level", config.isolation_level)

        self._state = PostgresConnectionState(connection, config, driver)
        return connection

    def close(self) -> None:
        if self._state:
            try:
                self._state.connection.close()
            finally:
                self._state = None

    def _ensure_connection(self):
        if not self._state:
            raise AdapterConnectionError("PostgresAdapter is not connected.")
        conn = self._state.connection
        if getattr(conn, "closed", False):
            self.logger.warning("PostgreSQL connection closed; reconnecting.")
            conn = self.connect(self._state.config)
        return conn

    def execute(self, sql: str, params: Sequence[Any] | None = None):
        connection = self._ensure_connection()
        cursor = connection.cursor()
        params = params or ()
        self._validate_params(sql, params)
        with time_call(
            "postgres.execute",
            self.logger,
            sql=sql,
            params=self._redact(params),
            threshold_ms=self.slow_query_ms,
        ):
            cursor.execute(sql, params)
        return cursor

    def executemany(
        self,
        sql: str,
        seq_of_params: Sequence[Sequence[Any]] | Iterable[Sequence[Any]],
    ):
        connection = self._ensure_connection()
        cursor = connection.cursor()
        seq = list(seq_of_params)
        for params in seq:
            self._validate_params(sql, params)
        with time_call(
            "postgres.executemany",
            self.logger,
            sql=sql,
            params="bulk",
            threshold_ms=self.slow_query_ms,
        ):
            cursor.executemany(sql, seq)
        return cursor

    def begin(self) -> None:
        if self._state and getattr(self._state.connection, "autocommit", False):
            return
        connection = self._ensure_connection()
        cursor = connection.cursor()
        cursor.execute("BEGIN")

    def commit(self) -> None:
        connection = self._ensure_connection()
        connection.commit()

    def rollback(self) -> None:
        connection = self._ensure_connection()
        connection.rollback()

    def last_insert_id(self, cursor: Any, table: str, pk_column: str) -> Any:
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("No RETURNING data available for last insert id.")
        return row[0]

    @staticmethod
    def _redact(params: Sequence[Any]) -> Sequence[Any]:
        redacted = []
        for value in params:
            if isinstance(value, str) and any(
                token in value.lower() for token in ("password", "secret", "token")
            ):
                redacted.append("***")
            else:
                redacted.append(value)
        return redacted

    @staticmethod
    def _count_placeholders(sql: str) -> int:
        count = 0
        idx = 0
        while idx < len(sql) - 1:
            if sql[idx] == "%" and sql[idx + 1] == "s":
                count += 1
                idx += 2
                continue
            if sql[idx] == "%" and sql[idx + 1] == "%":
                idx += 2
                continue
            idx += 1
        return count

    def _validate_params(self, sql: str, params: Sequence[Any]) -> None:
        placeholder_count = self._count_placeholders(sql)
        if placeholder_count == 0:
            if params:
                raise AdapterExecutionError(
                    "Parameters provided but SQL statement has no placeholders."
                )
            return
        if placeholder_count != len(params):
            raise AdapterExecutionError(
                f"Parameter count mismatch: expected {placeholder_count}, received {len(params)}."
            )
