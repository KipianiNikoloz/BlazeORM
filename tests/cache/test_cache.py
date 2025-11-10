from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.cache import InMemoryCache
from blazeorm.core import IntegerField, Model, StringField
from blazeorm.persistence import Session


class CountingAdapter(SQLiteAdapter):
    def __init__(self):
        super().__init__()
        self.execute_count = 0

    def execute(self, sql, params=None):
        self.execute_count += 1
        return super().execute(sql, params)


class User(Model):
    name = StringField(nullable=False)
    age = IntegerField(default=0)


def create_table(session):
    session.execute(
        'CREATE TABLE IF NOT EXISTS "user" (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER)'
    )


def test_second_level_cache_serves_subsequent_sessions(tmp_path):
    cache = InMemoryCache()
    adapter1 = CountingAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'cache.db'}")
    session1 = Session(adapter1, connection_config=config, cache_backend=cache)
    create_table(session1)
    session1.begin()
    user = User(name="Alice", age=30)
    session1.add(user)
    session1.commit()

    fetched = session1.get(User, id=user.id)
    assert fetched is user
    session1.close()

    adapter2 = CountingAdapter()
    session2 = Session(adapter2, connection_config=config, cache_backend=cache)
    result = session2.get(User, id=user.id)
    assert result.name == "Alice"
    assert adapter2.execute_count == 0
    session2.close()


def test_cache_invalidation_on_delete(tmp_path):
    cache = InMemoryCache()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'cache_delete.db'}")
    session = Session(CountingAdapter(), connection_config=config, cache_backend=cache)
    create_table(session)
    session.begin()
    user = User(name="Bob", age=22)
    session.add(user)
    session.commit()

    session.get(User, id=user.id)  # populate cache
    session.begin()
    session.delete(user)
    session.commit()
    session.close()

    session2 = Session(CountingAdapter(), connection_config=config, cache_backend=cache)
    assert session2.get(User, id=user.id) is None
    session2.close()
