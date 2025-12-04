from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import ForeignKey, IntegerField, ManyToManyField, Model, StringField
from blazeorm.schema import MigrationEngine, MigrationOperation, SchemaBuilder
from blazeorm.dialects import SQLiteDialect
from blazeorm.persistence import Session


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
        session.execute('INSERT INTO "article_category" (article_id, category_id) VALUES (?, ?)', (1, 1))
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
