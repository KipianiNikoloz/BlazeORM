"""Redaction helpers for DSNs and logged parameters."""

from __future__ import annotations

from typing import Any, Iterable

REDACTED_VALUE = "***"

_SENSITIVE_KEY_TOKENS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "apikey",
    "api_key",
    "access_key",
    "secret_key",
    "private_key",
    "privatekey",
    "sslkey",
    "ssl_key",
    "sslcert",
    "ssl_cert",
    "sslrootcert",
    "ssl_ca",
    "sslca",
)

_SENSITIVE_VALUE_TOKENS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "apikey",
    "api_key",
    "access_key",
    "secret_key",
    "private_key",
    "privatekey",
    "bearer",
    "authorization",
)


def _compact(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum())


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    compact = _compact(normalized)
    for token in _SENSITIVE_KEY_TOKENS:
        token_compact = _compact(token)
        if token in normalized or token_compact in compact:
            return True
    return False


def is_sensitive_value(value: str) -> bool:
    normalized = value.lower()
    return any(token in normalized for token in _SENSITIVE_VALUE_TOKENS)


def redact_query_params(query: dict[str, str]) -> dict[str, str]:
    return {key: REDACTED_VALUE if is_sensitive_key(key) else val for key, val in query.items()}


def redact_value(value: Any, *, key: str | None = None) -> Any:
    if key is not None and is_sensitive_key(str(key)):
        return REDACTED_VALUE
    if isinstance(value, dict):
        return {k: redact_value(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, bytes):
        decoded = value.decode("utf-8", errors="ignore")
        if decoded and is_sensitive_value(decoded):
            return REDACTED_VALUE
        return value
    if isinstance(value, str):
        if is_sensitive_value(value):
            return REDACTED_VALUE
        return value
    return value


def redact_params(params: Iterable[Any]) -> list[Any]:
    return [redact_value(value) for value in params]
