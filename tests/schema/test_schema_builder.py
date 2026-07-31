import logging

import pytest

from blazeorm.core import (
    ForeignKey,
    Index,
    IntegerField,
    ManyToManyField,
    Model,
    StringField,
    UniqueConstraint,
)
from blazeorm.dialects import MySQLDialect, PostgresDialect, SQLiteDialect
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


class Membership(Model):
    tenant = IntegerField(nullable=False, db_column="tenant_id")
    user = IntegerField(nullable=False, db_column="user_id")
    status = StringField(nullable=False)

    class Meta:
        constraints = (UniqueConstraint(fields=("tenant", "user"), name="uq_membership_owner"),)
        indexes = (Index(fields=("status", "tenant"), name="idx_membership_lookup"),)


class GeneratedNames(Model):
    tenant = IntegerField(nullable=False)
    slug = StringField(nullable=False)

    class Meta:
        constraints = (UniqueConstraint(fields=("tenant", "slug")),)
        indexes = (Index(fields=("slug", "tenant")),)


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


@pytest.mark.parametrize("dialect", [SQLiteDialect(), PostgresDialect(), MySQLDialect()])
def test_create_table_sql_includes_named_composite_unique_constraint(dialect):
    sql = SchemaBuilder(dialect).create_table_sql(Membership)
    constraint = dialect.quote_identifier("uq_membership_owner")
    tenant = dialect.quote_identifier("tenant_id")
    user = dialect.quote_identifier("user_id")

    assert f"CONSTRAINT {constraint} UNIQUE ({tenant}, {user})" in sql


def test_create_table_sql_generates_deterministic_constraint_name():
    sql = SchemaBuilder(SQLiteDialect()).create_table_sql(GeneratedNames)

    assert 'CONSTRAINT "uq_generated_names_tenant_slug" UNIQUE ("tenant", "slug")' in sql


@pytest.mark.parametrize("dialect", [SQLiteDialect(), PostgresDialect(), MySQLDialect()])
def test_composite_index_create_and_drop_sql_uses_dialect(dialect):
    local_builder = SchemaBuilder(dialect)
    table = dialect.format_table("membership")
    name = dialect.quote_identifier("idx_membership_lookup")
    status = dialect.quote_identifier("status")
    tenant = dialect.quote_identifier("tenant_id")

    create_sql = local_builder.create_index_sql(Membership)
    drop_sql = local_builder.drop_index_sql(Membership)

    create_prefix = "CREATE INDEX" if dialect.name == "mysql" else "CREATE INDEX IF NOT EXISTS"
    assert create_sql == [f"{create_prefix} {name} ON {table} ({status}, {tenant})"]
    expected_drop = (
        f"DROP INDEX {name} ON {table}"
        if dialect.name == "mysql"
        else f"DROP INDEX IF EXISTS {name}"
    )
    assert drop_sql == [expected_drop]


def test_composite_index_generates_deterministic_name():
    sql = SchemaBuilder(SQLiteDialect()).create_index_sql(GeneratedNames)

    assert sql == [
        'CREATE INDEX IF NOT EXISTS "idx_generated_names_slug_tenant" '
        'ON "generated_names" ("slug", "tenant")'
    ]
