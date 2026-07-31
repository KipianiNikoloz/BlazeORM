import pytest

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import ForeignKey, IntegerField, ManyToManyField, Model, StringField
from blazeorm.dialects import SQLiteDialect
from blazeorm.persistence import Session
from blazeorm.schema import MigrationEngine, MigrationOperation, SchemaBuilder


class User(Model):
    name = StringField(nullable=False)
    age = IntegerField()


class Author(Model):
    name = StringField(nullable=False)


class Post(Model):
    title = StringField()
    author = ForeignKey(Author, related_name="posts")


class Category(Model):
    name = StringField(nullable=False)


class Article(Model):
    title = StringField()
    author = ForeignKey(Author, related_name="articles")
    categories = ManyToManyField(Category, related_name="articles")


def create_user_table(session: Session) -> None:
    session.execute(
        'CREATE TABLE "user" (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER)'
    )


def create_populated_user_session(tmp_path, filename: str = "terminals.db") -> Session:
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / filename}")
    session = Session(adapter, connection_config=config)
    create_user_table(session)
    session.execute('INSERT INTO "user" (name, age) VALUES (?, ?)', ("Alice", 30))
    session.execute('INSERT INTO "user" (name, age) VALUES (?, ?)', ("Bob", 20))
    session.execute('INSERT INTO "user" (name, age) VALUES (?, ?)', ("Cara", 20))
    return session


def create_author_post_tables(session: Session) -> None:
    session.execute(
        'CREATE TABLE "author" (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)'
    )
    session.execute(
        'CREATE TABLE "post" (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, author INTEGER)'
    )


def create_article_category_tables(session: Session) -> None:
    builder = SchemaBuilder(SQLiteDialect())
    ops = [
        MigrationOperation(sql=builder.create_table_sql(Author)),
        MigrationOperation(sql=builder.create_table_sql(Category)),
        MigrationOperation(sql=builder.create_table_sql(Article)),
    ]
    ops.extend(MigrationOperation(sql=stmt) for stmt in builder.create_many_to_many_sql(Article))
    engine = MigrationEngine(session.adapter, session.dialect)
    engine.apply("app", "0002", ops)


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


def test_manager_iteration_uses_context_session(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'ctx.db'}")
    create_sql = 'CREATE TABLE "user" (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER)'
    session = Session(adapter, connection_config=config)
    session.execute(create_sql)
    session.execute('INSERT INTO "user" (name, age) VALUES (?, ?)', ("Zoe", 22))
    with session:
        users = list(User.objects.order_by("id"))
    assert users and users[0].name == "Zoe"


def test_select_related_attaches_related_instance(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'select_related.db'}")
    session = Session(adapter, connection_config=config)
    create_author_post_tables(session)
    session.execute('INSERT INTO "author" (name) VALUES (?)', ("Alice",))
    session.execute('INSERT INTO "post" (title, author) VALUES (?, ?)', ("Hello", 1))
    with session:
        posts = list(Post.objects.select_related("author"))
    assert posts
    assert posts[0].author.name == "Alice"


def test_prefetch_related_loads_reverse_relation(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'prefetch.db'}")
    session = Session(adapter, connection_config=config)
    create_author_post_tables(session)
    session.execute('INSERT INTO "author" (name) VALUES (?)', ("Bob",))
    session.execute('INSERT INTO "author" (name) VALUES (?)', ("Cara",))
    session.execute('INSERT INTO "post" (title, author) VALUES (?, ?)', ("One", 1))
    session.execute('INSERT INTO "post" (title, author) VALUES (?, ?)', ("Two", 1))
    with session:
        authors = list(session.query(Author).prefetch_related("posts").order_by("id"))
    assert len(authors[0].posts) == 2
    assert authors[1].posts == []


def test_nested_select_and_prefetch_with_m2m_and_fk(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'nested.db'}")
    session = Session(adapter, connection_config=config)
    create_article_category_tables(session)
    with session:
        session.execute('INSERT INTO "author" (name) VALUES (?)', ("Dana",))
        session.execute('INSERT INTO "category" (name) VALUES (?)', ("Perf",))
        session.execute('INSERT INTO "article" (title, author) VALUES (?, ?)', ("Deep Dive", 1))
        # through table name article_category
        session.execute(
            'INSERT INTO "article_category" (article_id, category_id) VALUES (?, ?)', (1, 1)
        )
    with session:
        articles = list(
            session.query(Article)
            .select_related("author")
            .prefetch_related("categories", "author__articles")
        )
    assert len(articles) == 1
    assert articles[0].author.name == "Dana"
    assert [c.name for c in articles[0].categories] == ["Perf"]
    assert articles[0].author.articles[0].title == "Deep Dive"


def test_prefetch_with_empty_m2m_results(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'empty_m2m.db'}")
    session = Session(adapter, connection_config=config)
    create_article_category_tables(session)
    with session:
        session.execute('INSERT INTO "author" (name) VALUES (?)', ("Empty",))
        session.execute('INSERT INTO "article" (title, author) VALUES (?, ?)', ("Lonely", 1))
    with session:
        articles = list(session.query(Article).prefetch_related("categories"))
    assert articles
    assert articles[0].categories == []


def test_queryset_first_returns_one_or_none(tmp_path):
    session = create_populated_user_session(tmp_path, "first.db")
    assert session.query(User).order_by("name").first().name == "Alice"
    assert session.query(User).filter(name="Missing").first() is None
    assert session.query(User).limit(0).first() is None


def test_queryset_get_enforces_exactly_one_result(tmp_path):
    from blazeorm.query import DoesNotExist, MultipleObjectsReturned

    session = create_populated_user_session(tmp_path, "get.db")
    assert session.query(User).get(name="Alice").age == 30
    with pytest.raises(DoesNotExist, match="User"):
        session.query(User).get(name="Missing")
    with pytest.raises(MultipleObjectsReturned, match="User"):
        session.query(User).get(age=20)


def test_queryset_count_and_exists_respect_slicing(tmp_path):
    session = create_populated_user_session(tmp_path, "aggregate.db")
    query = session.query(User).filter(age__gte=20).order_by("name").offset(1).limit(1)
    assert query.count() == 1
    assert query.exists() is True
    assert session.query(User).filter(age__gt=100).exists() is False
    assert session.query(User).limit(0).count() == 0
    assert session.query(User).limit(0).exists() is False


def test_manager_terminal_methods_use_context_session(tmp_path):
    session = create_populated_user_session(tmp_path, "manager-terminals.db")
    with session:
        assert User.objects.get(name="Alice").name == "Alice"
        assert User.objects.first() is not None
        assert User.objects.count() == 3
        assert User.objects.filter(name="Missing").exists() is False


def test_values_returns_requested_fields_without_model_hydration(tmp_path):
    session = create_populated_user_session(tmp_path, "values.db")

    rows = (
        session.query(User)
        .filter(age=20)
        .order_by("name")
        .limit(2)
        .values("name", "age")
    )

    assert rows == [{"name": "Bob", "age": 20}, {"name": "Cara", "age": 20}]
    assert session.identity_map.values() == []


def test_values_list_supports_tuples_flat_results_and_manager(tmp_path):
    session = create_populated_user_session(tmp_path, "values-list.db")

    assert session.query(User).order_by("id").values_list("name", "age") == [
        ("Alice", 30),
        ("Bob", 20),
        ("Cara", 20),
    ]
    assert session.query(User).order_by("id").values_list("name", flat=True) == [
        "Alice",
        "Bob",
        "Cara",
    ]
    with session:
        assert User.objects.filter(age=20).order_by("name").values("name") == [
            {"name": "Bob"},
            {"name": "Cara"},
        ]


@pytest.mark.parametrize("method", ["values", "values_list"])
def test_projections_require_fields_and_bound_session(method):
    query = User.objects.all()

    with pytest.raises(ValueError, match="at least one field"):
        getattr(query, method)()
    with pytest.raises(RuntimeError, match="requires a bound Session"):
        getattr(query, method)("name")


def test_values_list_flat_requires_exactly_one_field(tmp_path):
    session = create_populated_user_session(tmp_path, "flat-error.db")

    with pytest.raises(ValueError, match="exactly one field"):
        session.query(User).values_list("name", "age", flat=True)


@pytest.mark.parametrize("method", ["first", "get", "count", "exists"])
def test_terminal_methods_require_bound_session(method):
    query = User.objects.all()
    with pytest.raises(RuntimeError, match="requires a bound Session"):
        getattr(query, method)()
