from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import IntegerField, Model, StringField
from blazeorm.dialects import SQLiteDialect
from blazeorm.schema import MigrationEngine, MigrationOperation, SchemaBuilder


class Article(Model):
    title = StringField(nullable=False)
    body = StringField()
    views = IntegerField(default=0)


def test_migration_engine_applies_operations(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'migrate.db'}")
    adapter.connect(config)
    engine = MigrationEngine(adapter, SQLiteDialect())
    builder = SchemaBuilder(SQLiteDialect())

    operations = [MigrationOperation(sql=builder.create_table_sql(Article))]
    engine.apply("testapp", "0001_initial", operations)

    cursor = adapter.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='article'")
    assert cursor.fetchone() is not None

    applied = engine.applied_migrations()
    assert ("testapp", "0001_initial") in applied
