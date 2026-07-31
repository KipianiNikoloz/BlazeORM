from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.cache import InMemoryCache
from blazeorm.core import Model, StringField
from blazeorm.persistence import Session


class Product(Model):
    name = StringField(nullable=False)


def make_session(tmp_path, *, cache=None):
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'bulk-create.db'}")
    session = Session(SQLiteAdapter(), connection_config=config, cache_backend=cache)
    session.execute(
        'CREATE TABLE IF NOT EXISTS "product" '
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)"
    )
    return session


def test_bulk_create_persists_in_order_with_generated_keys_and_caches(tmp_path):
    cache = InMemoryCache()
    session = make_session(tmp_path, cache=cache)
    products = [Product(name="One"), Product(name="Two"), Product(name="Three")]

    created = session.bulk_create(products)

    assert created == products
    assert [product.id for product in products] == [1, 2, 3]
    assert all(product._persisted for product in products)
    assert [row[0] for row in session.execute('SELECT name FROM "product" ORDER BY id')] == [
        "One",
        "Two",
        "Three",
    ]
    for product in products:
        assert session.identity_map.get(Product, product.id) is product
        assert cache.get(Product, product.id) == product.to_dict()


def test_bulk_create_empty_collection_does_not_open_transaction(tmp_path):
    session = make_session(tmp_path)
    depth_before = session.transaction_manager.depth

    assert session.bulk_create([]) == []

    assert session.transaction_manager.depth == depth_before
