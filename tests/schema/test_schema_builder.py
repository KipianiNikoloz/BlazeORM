import logging

from blazeorm.core import IntegerField, ManyToManyField, Model, StringField
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
