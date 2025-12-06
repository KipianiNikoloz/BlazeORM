import os
import uuid

import pytest

from blazeorm.adapters import ConnectionConfig
from blazeorm.adapters.postgres import PostgresAdapter


def _require_postgres_adapter():
    try:
        import psycopg  # noqa: F401
    except ImportError:
        pytest.skip("psycopg driver not installed")
    dsn = os.getenv("BLAZE_POSTGRES_DSN")
    if not dsn:
        pytest.skip("BLAZE_POSTGRES_DSN not set; skipping Postgres integration test")
    adapter = PostgresAdapter()
    config = ConnectionConfig.from_dsn(dsn)
    try:
        adapter.connect(config)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Cannot connect to Postgres for integration test: {exc}")
    return adapter


def test_postgres_roundtrip():
    adapter = _require_postgres_adapter()
    table = f"blaze_pg_integration_{uuid.uuid4().hex[:8]}"
    try:
        adapter.begin()
        adapter.execute(
            f'CREATE TABLE IF NOT EXISTS "{table}" (id SERIAL PRIMARY KEY, name TEXT)'
        )
        adapter.execute(
            f'INSERT INTO "{table}" (name) VALUES (%s)', ("pg-ok",)
        )
        adapter.commit()

        cursor = adapter.execute(
            f'SELECT name FROM "{table}" WHERE id = %s', (1,)
        )
        row = cursor.fetchone()
        assert row and row[0] == "pg-ok"
    finally:
        try:
            adapter.execute(f'DROP TABLE IF EXISTS "{table}"')
            adapter.commit()
        except Exception:
            pass
        adapter.close()
