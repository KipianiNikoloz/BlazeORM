import sqlite3

import pytest

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter


@pytest.fixture
def adapter(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'test.db'}")
    adapter.connect(config)
    yield adapter
    adapter.close()


def test_connect_creates_database(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'connect.db'}")
    connection = adapter.connect(config)
    assert isinstance(connection, sqlite3.Connection)
    adapter.close()


def test_execute_and_last_insert_id(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'exec.db'}")
    adapter.connect(config)
    adapter.execute("CREATE TABLE example (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    cursor = adapter.execute("INSERT INTO example (name) VALUES (?)", ("Alice",))
    inserted_id = adapter.last_insert_id(cursor, "example", "id")
    assert inserted_id == 1
    rows = adapter.execute("SELECT name FROM example WHERE id = ?", (inserted_id,)).fetchall()
    assert rows[0][0] == "Alice"
    adapter.close()


def test_transaction_commit_and_rollback(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'txn.db'}")
    adapter.connect(config)
    adapter.execute("CREATE TABLE item (id INTEGER PRIMARY KEY, value INTEGER)")

    adapter.begin()
    adapter.execute("INSERT INTO item (value) VALUES (?)", (10,))
    adapter.commit()
    count = adapter.execute("SELECT COUNT(*) FROM item").fetchone()[0]
    assert count == 1

    adapter.begin()
    adapter.execute("INSERT INTO item (value) VALUES (?)", (20,))
    adapter.rollback()
    count_after = adapter.execute("SELECT COUNT(*) FROM item").fetchone()[0]
    assert count_after == 1
    adapter.close()


def test_in_memory_database():
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url="sqlite:///:memory:")
    adapter.connect(config)
    adapter.execute("CREATE TABLE sample (value TEXT)")
    adapter.execute("INSERT INTO sample (value) VALUES (?)", ("hello",))
    row = adapter.execute("SELECT value FROM sample").fetchone()
    assert row[0] == "hello"
    adapter.close()
