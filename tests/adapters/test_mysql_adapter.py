import pytest

from blazeorm.adapters import ConnectionConfig
from blazeorm.adapters.mysql import MySQLAdapter


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.last_params = None
        self.lastrowid = 1

    def execute(self, sql, params=None):
        self.executed.append(sql)
        self.last_params = params

    def executemany(self, sql, seq):
        self.executed.append(sql)
        self.last_params = list(seq)


class FakeConnection:
    def __init__(self):
        self.autocommit = lambda value: setattr(self, "_autocommit", value)
        self._autocommit = False
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return FakeCursor()

    def close(self):
        self.closed = True

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FakeDriver:
    def __init__(self):
        self.connections = []

    def connect(self, **options):
        conn = FakeConnection()
        conn.options = options
        self.connections.append(conn)
        return conn


@pytest.fixture
def fake_driver(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr("blazeorm.adapters.mysql._load_driver", lambda: driver)
    return driver


def test_mysql_adapter_connects(fake_driver):
    adapter = MySQLAdapter()
    config = ConnectionConfig.from_dsn("mysql://user:secret@localhost:3306/dbname")
    connection = adapter.connect(config)
    assert connection in fake_driver.connections
    assert connection._autocommit is False


def test_mysql_execute_validates_params(fake_driver):
    adapter = MySQLAdapter()
    config = ConnectionConfig.from_dsn("mysql://localhost/db")
    adapter.connect(config)
    cursor = adapter.execute("SELECT * FROM foo WHERE id = %s", (1,))
    assert cursor.last_params == (1,)
    with pytest.raises(ValueError):
        adapter.execute("SELECT * FROM foo WHERE id = %s", ())


def test_mysql_last_insert_id(fake_driver):
    adapter = MySQLAdapter()
    config = ConnectionConfig.from_dsn("mysql://localhost/db")
    adapter.connect(config)
    cursor = adapter.execute("INSERT INTO foo VALUES (%s)", (1,))
    cursor.lastrowid = 42
    assert adapter.last_insert_id(cursor, "foo", "id") == 42


def test_missing_driver(monkeypatch):
    monkeypatch.setattr("blazeorm.adapters.mysql._load_driver", lambda: None)
    adapter = MySQLAdapter()
    config = ConnectionConfig.from_dsn("mysql://localhost/db")
    with pytest.raises(RuntimeError):
        adapter.connect(config)
