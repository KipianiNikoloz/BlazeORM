import logging
from urllib.parse import parse_qs, urlparse

import pytest

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.dialects import SQLiteDialect
from blazeorm.persistence import Session
from blazeorm.schema import MigrationEngine, MigrationOperation
from blazeorm.security.dsns import parse_dsn
from blazeorm.security.migrations import confirm_destructive_operation
from blazeorm.security.redaction import redact_params


def test_parse_dsn_and_redact():
    dsn = "postgres://user:secret@localhost:5432/database"
    config = parse_dsn(dsn)
    assert config.password == "secret"
    assert config.redacted() == "postgres://user:***@localhost:5432/database"


def test_confirm_destructive_operation_requires_force():
    with pytest.raises(RuntimeError):
        confirm_destructive_operation("DROP TABLE")
    confirm_destructive_operation("DROP TABLE", force=True)


def test_connection_config_from_dsn_redacts():
    config = ConnectionConfig.from_dsn("postgres://user:secret@localhost:5432/database")
    assert config.dsn is not None
    assert config.redacted_dsn() == "postgres://user:***@localhost:5432/database"


def test_connection_config_redacts_sensitive_query_params():
    dsn = (
        "postgres://user:secret@localhost:5432/database"
        "?password=hunter2&sslkey=/tmp/key.pem&ssl_ca=/tmp/ca.pem&token=abc&sslmode=require"
    )
    config = ConnectionConfig.from_dsn(dsn)
    redacted = config.redacted_dsn()
    parsed = urlparse(redacted)
    query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    assert query["password"] == "***"
    assert query["sslkey"] == "***"
    assert query["ssl_ca"] == "***"
    assert query["token"] == "***"
    assert query["sslmode"] == "require"


def test_connection_config_from_env(monkeypatch):
    monkeypatch.setenv("BLAZE_DSN", "sqlite:///:memory:")
    config = ConnectionConfig.from_env("BLAZE_DSN", autocommit=True)
    assert config.source == "BLAZE_DSN"
    assert config.autocommit is True
    assert config.redacted_dsn() == "sqlite:///:memory:"


def test_session_accepts_dsn_argument(tmp_path):
    adapter = SQLiteAdapter()
    dsn = f"sqlite:///{tmp_path / 'security_session.db'}"
    session = Session(adapter, dsn=dsn)
    session.execute("SELECT 1")
    assert session.connection_config.dsn is not None
    session.close()


def test_session_rejects_dual_connection_config(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'conflict.db'}")
    with pytest.raises(ValueError):
        Session(adapter, connection_config=config, dsn="sqlite:///:memory:")


def test_destructive_migration_operation_requires_force(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger="blazeorm.schema.migration")
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'destructive.db'}")
    adapter.connect(config)
    engine = MigrationEngine(adapter, SQLiteDialect())
    operations = [
        MigrationOperation(
            sql="DROP TABLE IF EXISTS foo", destructive=True, description="drop foo table"
        )
    ]
    with pytest.raises(RuntimeError):
        engine.apply("app", "0002_drop", operations)
    assert any("Destructive migration detected" in record.message for record in caplog.records)

    caplog.clear()
    operations[0].force = True
    engine.apply("app", "0002_drop_force", operations)
    assert any("Destructive migration detected" in record.message for record in caplog.records)


def test_redact_params_masks_sensitive_values():
    params = [
        "plain",
        "password=hunter2",
        {"token": "abc", "count": 1},
        ("Bearer abc",),
        b"secret=bytes",
    ]
    redacted = redact_params(params)
    assert redacted[0] == "plain"
    assert redacted[1] == "***"
    assert redacted[2]["token"] == "***"
    assert redacted[2]["count"] == 1
    assert redacted[3][0] == "***"
    assert redacted[4] == "***"
