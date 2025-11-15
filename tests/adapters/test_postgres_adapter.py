import types

import pytest

from blazeorm.adapters import ConnectionConfig
from blazeorm.adapters.postgres import PostgresAdapter, _load_driver


class FakeCursor:
    def __init__(self):
        self.statements = []
        self.last_params = None
        self._fetch_rows = [(1,)]

    def execute(self, sql, params=None):
        self.statements.append(sql)
        self.last_params = params

    def executemany(self, sql, seq):
        self.statements.append(sql)
        self.last_params = list(seq)

    def fetchone(self):
        return self._fetch_rows.pop(0) if self._fetch_rows else None


class FakeConnection:
    def __init__(self):
        self.autocommit = False
        self.closed = False
        self.cursor_calls = 0

    def cursor(self):
        self.cursor_calls += 1
        return FakeCursor()

    def close(self):
        self.closed = True

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeDriver:
    def __init__(self):
        self.connections = []

    def connect(self, dsn, **options):
        conn = FakeConnection()
        conn.dsn = dsn
        conn.options = options
        self.connections.append(conn)
        return conn


@pytest.fixture
def fake_driver(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr("blazeorm.adapters.postgres._load_driver", lambda: driver)
    return driver


def test_connects_using_psycopg_driver(fake_driver):
    adapter = PostgresAdapter()
    config = ConnectionConfig.from_dsn("postgresql://user:secret@localhost:5432/dbname")
    connection = adapter.connect(config)
    assert connection in fake_driver.connections
    assert connection.autocommit is False


def test_execute_runs_sql_and_validates_params(fake_driver):
    adapter = PostgresAdapter()
    config = ConnectionConfig.from_dsn("postgresql://localhost/db")
    adapter.connect(config)
    cursor = adapter.execute("SELECT * FROM foo WHERE id = %s", (1,))
    assert cursor.last_params == (1,)
    with pytest.raises(ValueError):
        adapter.execute("SELECT * FROM foo WHERE id = %s", ())


def test_last_insert_id_reads_returning(fake_driver):
    adapter = PostgresAdapter()
    config = ConnectionConfig.from_dsn("postgresql://localhost/db")
    adapter.connect(config)
    cursor = adapter.execute("INSERT INTO foo VALUES (%s) RETURNING id", (1,))
    assert adapter.last_insert_id(cursor, "foo", "id") == 1


def test_missing_driver_raises(monkeypatch):
    monkeypatch.setattr("blazeorm.adapters.postgres._load_driver", lambda: None)
    adapter = PostgresAdapter()
    config = ConnectionConfig.from_dsn("postgresql://localhost/db")
    with pytest.raises(RuntimeError):
        adapter.connect(config)
