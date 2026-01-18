import logging

from blazeorm.core import ForeignKey, IntegerField, ManyToManyField, Model, StringField
from blazeorm.dialects import SQLiteDialect
from blazeorm.schema import SchemaBuilder

dialect = SQLiteDialect()
builder = SchemaBuilder(dialect)


class User(Model):
    name = StringField(nullable=False)
    age = IntegerField(default=0)


class Group(Model):
    name = StringField(nullable=False)
    members = ManyToManyField(User, related_name="groups")


class Author(Model):
    name = StringField(nullable=False)


class Post(Model):
    title = StringField()
    author = ForeignKey(Author, related_name="posts", on_delete="CASCADE")


class Indexed(Model):
    slug = StringField(index=True)


def test_create_table_sql():
    sql = builder.create_table_sql(User)
    expected = 'CREATE TABLE IF NOT EXISTS "user" ("id" INTEGER NOT NULL PRIMARY KEY, "name" TEXT NOT NULL, "age" INTEGER DEFAULT 0)'
    assert sql == expected


def test_drop_table_sql():
    sql = builder.drop_table_sql(User)
    assert sql == 'DROP TABLE IF EXISTS "user"'


def test_drop_table_logs_warning(caplog):
    caplog.set_level(logging.WARNING, logger="blazeorm.schema.builder")
    local_builder = SchemaBuilder(SQLiteDialect())
    local_builder.drop_table_sql(User)
    assert any("DROP TABLE generated" in record.message for record in caplog.records)


def test_m2m_through_table_sql():
    builder = SchemaBuilder(SQLiteDialect())
    stmts = builder.create_many_to_many_sql(Group)
    assert len(stmts) == 1
    sql = stmts[0]
    assert "CREATE TABLE IF NOT EXISTS" in sql
    assert "user_id" in sql and "group_id" in sql
    assert "FOREIGN KEY" in sql


def test_create_table_sql_includes_foreign_keys():
    sql = builder.create_table_sql(Post)
    assert 'FOREIGN KEY ("author")' in sql
    assert 'REFERENCES "author" ("id")' in sql
    assert "ON DELETE CASCADE" in sql


def test_create_index_sql():
    sql = builder.create_index_sql(Indexed)
    assert sql == ['CREATE INDEX IF NOT EXISTS "idx_indexed_slug" ON "indexed" ("slug")']


def test_drop_index_sql_logs_warning(caplog):
    caplog.set_level(logging.WARNING, logger="blazeorm.schema.builder")
    sql = builder.drop_index_sql(Indexed)
    assert sql == ['DROP INDEX IF EXISTS "idx_indexed_slug"']
    assert any("DROP INDEX generated" in record.message for record in caplog.records)
