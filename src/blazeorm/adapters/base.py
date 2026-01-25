"""
Adapter protocol definitions for BlazeORM.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from ..dialects.base import Dialect
from ..security.dsns import DSNConfig, parse_dsn


class AdapterError(RuntimeError):
    """Base error for adapter-related failures."""


class AdapterConfigurationError(AdapterError):
    """Raised when configuration or required dependencies are invalid."""


class AdapterConnectionError(AdapterError):
    """Raised when establishing or using a connection fails."""


class AdapterExecutionError(AdapterError):
    """Raised when SQL execution or parameter validation fails."""


class AdapterTransactionError(AdapterError):
    """Raised when transaction operations fail."""


@dataclass
class SSLConfig:
    mode: str | None = None
    rootcert: str | None = None
    cert: str | None = None
    key: str | None = None
    ca: str | None = None
    check_hostname: bool | None = None

    def postgres_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {}
        if self.mode:
            options["sslmode"] = self.mode
        if self.rootcert:
            options["sslrootcert"] = self.rootcert
        if self.cert:
            options["sslcert"] = self.cert
        if self.key:
            options["sslkey"] = self.key
        return options

    def mysql_options(self) -> dict[str, Any]:
        ssl: dict[str, Any] = {}
        if self.ca:
            ssl["ca"] = self.ca
        if self.cert:
            ssl["cert"] = self.cert
        if self.key:
            ssl["key"] = self.key
        if self.check_hostname is not None:
            ssl["check_hostname"] = self.check_hostname
        if not ssl:
            return {}
        return {"ssl": ssl}


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _parse_bool(value: str, *, key: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise AdapterConfigurationError(f"Invalid boolean value for '{key}': {value!r}")


def _parse_float(value: str, *, key: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise AdapterConfigurationError(f"Invalid float value for '{key}': {value!r}") from exc


def _parse_int(value: str, *, key: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise AdapterConfigurationError(f"Invalid integer value for '{key}': {value!r}") from exc


def _pop_bool(query: dict[str, str], key: str) -> bool | None:
    if key not in query:
        return None
    return _parse_bool(query.pop(key), key=key)


def _pop_float(query: dict[str, str], key: str) -> float | None:
    if key not in query:
        return None
    return _parse_float(query.pop(key), key=key)


def _parse_ssl(query: dict[str, str]) -> SSLConfig | None:
    ssl = SSLConfig()
    if "sslmode" in query:
        ssl.mode = query.pop("sslmode")
    if "sslrootcert" in query:
        ssl.rootcert = query.pop("sslrootcert")
    if "sslcert" in query:
        ssl.cert = query.pop("sslcert")
    if "sslkey" in query:
        ssl.key = query.pop("sslkey")
    if "ssl_ca" in query:
        ssl.ca = query.pop("ssl_ca")
    if "ssl_cert" in query:
        ssl.cert = query.pop("ssl_cert")
    if "ssl_key" in query:
        ssl.key = query.pop("ssl_key")
    if "ssl_check_hostname" in query:
        ssl.check_hostname = _parse_bool(query.pop("ssl_check_hostname"), key="ssl_check_hostname")
    if any(
        [
            ssl.mode,
            ssl.rootcert,
            ssl.cert,
            ssl.key,
            ssl.ca,
            ssl.check_hostname is not None,
        ]
    ):
        return ssl
    return None


def _parse_option_values(query: dict[str, str]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    for key, value in query.items():
        if key == "connect_timeout":
            options[key] = _parse_int(value, key=key)
        else:
            options[key] = value
    return options


@dataclass
class ConnectionConfig:
    """
    Normalized connection configuration for adapters.
    """

    url: str
    autocommit: bool = False
    isolation_level: str | None = None
    timeout: float | None = None
    options: dict[str, Any] | None = None
    ssl: SSLConfig | None = None
    dsn: DSNConfig | None = None
    source: str | None = None

    @classmethod
    def from_dsn(cls, dsn: str, **kwargs: Any) -> "ConnectionConfig":
        """
        Build a connection config by parsing the DSN string.
        """

        parsed = parse_dsn(dsn)
        query = dict(parsed.query)

        parsed_autocommit = _pop_bool(query, "autocommit")
        parsed_timeout = _pop_float(query, "timeout")
        parsed_isolation_level = query.pop("isolation_level", None)
        parsed_ssl = _parse_ssl(query)
        options_from_dsn = _parse_option_values(query)

        options = dict(options_from_dsn)
        passed_options = kwargs.pop("options", None) or {}
        options.update(passed_options)

        autocommit = kwargs.pop("autocommit", parsed_autocommit)
        if autocommit is None:
            autocommit = False
        isolation_level = kwargs.pop("isolation_level", parsed_isolation_level)
        timeout = kwargs.pop("timeout", parsed_timeout)
        ssl = kwargs.pop("ssl", parsed_ssl)

        return cls(
            url=dsn,
            dsn=parsed,
            autocommit=autocommit,
            isolation_level=isolation_level,
            timeout=timeout,
            options=options or None,
            ssl=ssl,
            **kwargs,
        )

    @classmethod
    def from_env(cls, env_var: str, **kwargs: Any) -> "ConnectionConfig":
        """
        Build a config from an environment variable containing a DSN.
        """

        value = os.getenv(env_var)
        if not value:
            raise AdapterConfigurationError(f"Environment variable {env_var} is not set")
        return cls.from_dsn(value, source=env_var, **kwargs)

    def redacted_dsn(self) -> str:
        """
        Return a DSN safe for logging (credentials removed).
        """

        if self.dsn:
            return self.dsn.redacted()
        return self.url

    def descriptive_label(self) -> str:
        """
        Describe the config source for diagnostics.
        """

        redacted = self.redacted_dsn()
        if self.source:
            return f"{self.source} ({redacted})"
        return redacted


class DatabaseAdapter(Protocol):
    """
    Adapter interface exposing database operations used by higher layers.
    """

    dialect: Dialect
    slow_query_ms: int

    def connect(self, config: ConnectionConfig) -> Any:
        """
        Establish a connection handle using the supplied configuration.
        """

    def close(self) -> None:
        """
        Close underlying resources. Implementations should be idempotent.
        """

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        """
        Execute a single SQL statement returning a cursor-like object.
        """

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]) -> Any:
        """
        Execute a prepared statement against multiple parameter sets.
        """

    def begin(self) -> None:
        """
        Start a transaction or savepoint as appropriate for the backend.
        """

    def commit(self) -> None:
        """
        Commit the current transaction context.
        """

    def rollback(self) -> None:
        """
        Roll back the current transaction context.
        """

    def last_insert_id(self, cursor: Any, table: str, pk_column: str) -> Any:
        """
        Retrieve the primary key value generated by the previous insert.
        """
