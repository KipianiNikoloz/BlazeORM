import pytest

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.dialects import SQLiteDialect
from blazeorm.schema import MigrationEngine, MigrationOperation, SchemaBuilder
from blazeorm.security.dsns import parse_dsn
from blazeorm.security.migrations import confirm_destructive_operation


def test_parse_dsn_and_redact():
    dsn = "postgres://user:secret@localhost:5432/database"
    config = parse_dsn(dsn)
    assert config.password == "secret"
    assert config.redacted() == "postgres://user:***@localhost:5432/database"


def test_confirm_destructive_operation_requires_force():
    with pytest.raises(RuntimeError):
        confirm_destructive_operation("DROP TABLE")
    confirm_destructive_operation("DROP TABLE", force=True)


def test_destructive_migration_operation_requires_force(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'destructive.db'}")
    adapter.connect(config)
    engine = MigrationEngine(adapter, SQLiteDialect())
    operations = [
        MigrationOperation(sql="DROP TABLE IF EXISTS foo", destructive=True, description="drop foo table")
    ]
    with pytest.raises(RuntimeError):
        engine.apply("app", "0002_drop", operations)

    operations[0].force = True
    engine.apply("app", "0002_drop_force", operations)
