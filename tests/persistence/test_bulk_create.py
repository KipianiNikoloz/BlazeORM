import pytest

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.cache import InMemoryCache
from blazeorm.core import Model, StringField
from blazeorm.hooks import hooks
from blazeorm.persistence import Session
from blazeorm.validation import ValidationError


class Product(Model):
    name = StringField(nullable=False)


class OtherProduct(Model):
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


@pytest.mark.parametrize(
    ("instances", "error", "message"),
    [
        ([Product(name="One"), OtherProduct(name="Two")], ValueError, "same model"),
        (["not a model"], TypeError, "Model instances"),
    ],
)
def test_bulk_create_rejects_invalid_collection_shapes(tmp_path, instances, error, message):
    session = make_session(tmp_path)

    with pytest.raises(error, match=message):
        session.bulk_create(instances)

    assert session.execute('SELECT COUNT(*) FROM "product"').fetchone()[0] == 0


def test_bulk_create_rejects_duplicate_and_persisted_instances(tmp_path):
    session = make_session(tmp_path)
    duplicate = Product(name="Duplicate")

    with pytest.raises(ValueError, match="same instance"):
        session.bulk_create([duplicate, duplicate])

    existing = Product(name="Existing")
    session.bulk_create([existing])
    with pytest.raises(ValueError, match="already persisted"):
        session.bulk_create([existing])


def test_bulk_create_runs_save_hooks_once_in_input_order(tmp_path):
    session = make_session(tmp_path)
    products = [Product(name="One"), Product(name="Two")]
    events = []
    hooks.register(
        "before_save",
        lambda instance, **context: events.append(("before", instance.name)),
        model=Product,
    )
    hooks.register(
        "after_save",
        lambda instance, **context: events.append(("after", instance.name)),
        model=Product,
    )
    try:
        session.bulk_create(products)
    finally:
        hooks.clear()

    assert events == [
        ("before", "One"),
        ("after", "One"),
        ("before", "Two"),
        ("after", "Two"),
    ]


def test_bulk_create_failure_rolls_back_rows_and_restores_objects(tmp_path):
    session = make_session(tmp_path)
    valid = Product(name="Valid")
    invalid = Product()
    before = [(dict(obj._field_values), dict(obj._initial_state)) for obj in (valid, invalid)]

    with pytest.raises(ValidationError):
        session.bulk_create([valid, invalid])

    assert session.execute('SELECT COUNT(*) FROM "product"').fetchone()[0] == 0
    for obj, (field_values, initial_state) in zip((valid, invalid), before):
        assert obj._field_values == field_values
        assert obj._initial_state == initial_state
        assert obj._persisted is False
        assert session.identity_map.get(Product, getattr(obj, "id", None)) is None


def test_bulk_create_uses_savepoint_inside_outer_transaction(tmp_path):
    session = make_session(tmp_path)
    session.begin()
    product = Product(name="Nested")

    session.bulk_create([product])

    assert product.id == 1
    assert session.transaction_manager.depth == 1
    session.rollback()
    assert session.execute('SELECT COUNT(*) FROM "product"').fetchone()[0] == 0
