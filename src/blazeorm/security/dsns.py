"""DSN parsing and redaction utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DSNConfig:
    driver: str
    username: Optional[str]
    password: Optional[str]
    host: Optional[str]
    port: Optional[int]
    database: Optional[str]
    query: dict[str, str]

    def redacted(self) -> str:
        user_part = self.username or ""
        if user_part and self.password:
            user_part += ":***"
        if user_part:
            user_part += "@"
        host = self.host or "localhost"
        port = f":{self.port}" if self.port else ""
        db = f"/{self.database}" if self.database else ""
        return f"{self.driver}://{user_part}{host}{port}{db}" 


def parse_dsn(dsn: str) -> DSNConfig:
    from urllib.parse import urlparse, parse_qs

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
        query=query,
    )


def dsn_from_env(env_var: str) -> DSNConfig:
    value = os.getenv(env_var)
    if not value:
        raise ValueError(f"Environment variable {env_var} is not set")
    return parse_dsn(value)
