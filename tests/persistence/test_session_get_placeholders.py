import pytest

from blazeorm.adapters import ConnectionConfig
from blazeorm.core import Model, StringField
from blazeorm.dialects import MySQLDialect, PostgresDialect
from blazeorm.persistence import Session


class Dummy(Model):
    name = StringField()


class FakeCursor:
    def fetchone(self):
        return None


class FakeAdapter:
    def __init__(self, dialect):
        self.dialect = dialect
        self.sql_calls = []
        self.params_calls = []
        self.connected = False

    def connect(self, config):
        self.connected = True
        self.config = config

    def close(self):
        self.connected = False

    def execute(self, sql, params=None):
        self.sql_calls.append(sql)
        self.params_calls.append(params)
        return FakeCursor()

    def executemany(self, sql, seq_of_params):
        raise NotImplementedError

    def begin(self):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None

    def last_insert_id(self, cursor, table, pk_column):
        return None


@pytest.mark.parametrize(
    ("dialect", "dsn"),
    [
        (PostgresDialect(), "postgresql://user:secret@localhost:5432/dbname"),
        (MySQLDialect(), "mysql://user:secret@localhost:3306/dbname"),
    ],
)
def test_session_get_uses_dialect_placeholders(dialect, dsn):
    adapter = FakeAdapter(dialect)
    config = ConnectionConfig.from_dsn(dsn)
    session = Session(adapter, connection_config=config)
    try:
        result = session.get(Dummy, id=1)
    finally:
        session.close()
    assert result is None
    assert adapter.sql_calls
    sql = adapter.sql_calls[-1]
    params = adapter.params_calls[-1]
    placeholder = dialect.parameter_placeholder()
    assert f"= {placeholder}" in sql
    assert "?" not in sql
    assert params == [1]
