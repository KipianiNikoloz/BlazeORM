from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import IntegerField, Model, StringField
from blazeorm.persistence import Session


class User(Model):
    name = StringField(nullable=False)
    age = IntegerField()


def create_user_table(session: Session) -> None:
    session.execute(
        'CREATE TABLE "user" (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER)'
    )


def test_queryset_iteration_fetches_instances(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'iter.db'}")
    session = Session(adapter, connection_config=config)
    create_user_table(session)
    session.execute('INSERT INTO "user" (name, age) VALUES (?, ?)', ("Alice", 30))
    session.execute('INSERT INTO "user" (name, age) VALUES (?, ?)', ("Bob", 25))

    users = list(session.query(User).order_by("id"))
    assert [u.name for u in users] == ["Alice", "Bob"]
    assert users[0].age == 30


def test_queryset_iteration_reuses_identity_map(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'identity.db'}")
    session = Session(adapter, connection_config=config)
    create_user_table(session)
    session.execute('INSERT INTO "user" (name, age) VALUES (?, ?)', ("Eve", 40))

    first = list(session.query(User).filter(id=1))[0]
    second = list(session.query(User).filter(id=1))[0]
    assert first is second
    session.close()
