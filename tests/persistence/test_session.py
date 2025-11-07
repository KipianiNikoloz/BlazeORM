import pytest

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import IntegerField, Model, StringField
from blazeorm.persistence import Session


class User(Model):
    name = StringField(nullable=False)
    age = IntegerField(default=0)


def create_table(session: Session) -> None:
    session.execute(
        "CREATE TABLE IF NOT EXISTS \"user\" (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER)"
    )


def test_session_add_and_commit_inserts_row(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'session.db'}")
    session = Session(adapter, connection_config=config)
    create_table(session)
    session.begin()
    user = User(name="Alice", age=30)
    session.add(user)
    session.commit()

    cursor = session.execute("SELECT name, age FROM \"user\"")
    row = cursor.fetchone()
    assert row["name"] == "Alice"
    assert row["age"] == 30
    assert user.id is not None
    session.close()


def test_session_identity_map_returns_same_instance(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'identity.db'}")
    session = Session(adapter, connection_config=config)
    create_table(session)
    session.begin()
    session.execute("INSERT INTO \"user\" (name, age) VALUES (?, ?)", ("Bob", 25))
    session.commit()

    # Fetch twice should return same instance due to identity map
    first = session.get(User, id=1)
    second = session.get(User, id=1)
    assert first is second
    assert first.name == "Bob"
    session.close()


def test_session_delete_and_rollback(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'delete.db'}")
    session = Session(adapter, connection_config=config)
    create_table(session)
    session.begin()
    session.execute("INSERT INTO \"user\" (name, age) VALUES (?, ?)", ("Chris", 40))
    session.commit()

    user = session.get(User, id=1)
    session.begin()
    session.delete(user)
    session.rollback()
    remaining = session.execute("SELECT COUNT(*) FROM \"user\"").fetchone()[0]
    assert remaining == 1

    session.begin()
    session.delete(user)
    session.commit()
    remaining_after = session.execute("SELECT COUNT(*) FROM \"user\"").fetchone()[0]
    assert remaining_after == 0
    session.close()


def test_session_updates_dirty_instances(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'update.db'}")
    session = Session(adapter, connection_config=config)
    create_table(session)
    session.begin()
    user = User(name="Dana", age=22)
    session.add(user)
    session.commit()

    loaded = session.get(User, id=user.id)
    loaded.age = 23
    session.mark_dirty(loaded)
    session.begin()
    session.commit()

    updated_age = session.execute("SELECT age FROM \"user\" WHERE id = ?", (user.id,)).fetchone()[0]
    assert updated_age == 23
    session.close()


def test_session_transaction_context(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'context.db'}")
    session = Session(adapter, connection_config=config)
    create_table(session)

    with session.transaction():
        session.add(User(name="Eve", age=31))

    row = session.execute("SELECT COUNT(*) FROM \"user\"").fetchone()[0]
    assert row == 1
    session.close()


def test_nested_transactions_use_savepoints(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'nested.db'}")
    session = Session(adapter, connection_config=config)
    create_table(session)

    with session.transaction():
        session.add(User(name="Outer", age=44))
        with pytest.raises(RuntimeError):
            with session.transaction():
                session.add(User(name="Inner", age=18))
                raise RuntimeError("inner failure")

    rows = session.execute("SELECT name FROM \"user\" ORDER BY id").fetchall()
    assert [row["name"] for row in rows] == ["Outer"]
    session.close()
