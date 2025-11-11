"""DSN parsing and redaction utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse


@dataclass
class DSNConfig:
    driver: str
    username: Optional[str]
    password: Optional[str]
    host: Optional[str]
    port: Optional[int]
    database: Optional[str]
    path: str
    query: dict[str, str]

    def redacted(self) -> str:
        """
        Return the DSN with credentials redacted but structure preserved.
        """

        netloc = ""
        if self.username:
            netloc += self.username
            if self.password:
                netloc += ":***"
            netloc += "@"
        if self.host:
            netloc += self.host
        if self.port:
            netloc += f":{self.port}"

        query_string = urlencode(self.query) if self.query else ""

        # Build manually so we retain the double slash prefix even when netloc is empty
        result = f"{self.driver}://"
        if netloc:
            result += netloc
        result += self.path or ""
        if query_string:
            result += f"?{query_string}"
        return result


def parse_dsn(dsn: str) -> DSNConfig:
    parsed = urlparse(dsn)
    query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    password = parsed.password
    return DSNConfig(
        driver=parsed.scheme,
        username=parsed.username,
        password=password,
        host=parsed.hostname,
        port=parsed.port,
        database=parsed.path.lstrip("/") or None,
        path=parsed.path or "",
        query=query,
    )


def dsn_from_env(env_var: str) -> DSNConfig:
    value = os.getenv(env_var)
    if not value:
        raise ValueError(f"Environment variable {env_var} is not set")
    return parse_dsn(value)
