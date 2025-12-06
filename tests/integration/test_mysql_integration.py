import os
import uuid

import pytest

from blazeorm.adapters import ConnectionConfig
from blazeorm.adapters.mysql import MySQLAdapter


def _require_mysql_adapter():
    try:
        import pymysql  # noqa: F401
    except ImportError:
        try:
            import MySQLdb  # type: ignore  # noqa: F401
        except ImportError:
            pytest.skip("No MySQL driver installed")
    dsn = os.getenv("BLAZE_MYSQL_DSN")
    if not dsn:
        pytest.skip("BLAZE_MYSQL_DSN not set; skipping MySQL integration test")
    adapter = MySQLAdapter()
    config = ConnectionConfig.from_dsn(dsn)
    try:
        adapter.connect(config)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Cannot connect to MySQL for integration test: {exc}")
    return adapter


def test_mysql_roundtrip():
    adapter = _require_mysql_adapter()
    table = f"blaze_mysql_integration_{uuid.uuid4().hex[:8]}"
    try:
        adapter.begin()
        adapter.execute(
            f"CREATE TABLE IF NOT EXISTS `{table}` (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100))"
        )
        adapter.execute(
            f"INSERT INTO `{table}` (name) VALUES (%s)", ("mysql-ok",)
        )
        adapter.commit()

        cursor = adapter.execute(
            f"SELECT name FROM `{table}` WHERE id = %s", (1,)
        )
        row = cursor.fetchone()
        assert row and row[0] == "mysql-ok"
    finally:
        try:
            adapter.execute(f"DROP TABLE IF EXISTS `{table}`")
            adapter.commit()
        except Exception:
            pass
        adapter.close()
