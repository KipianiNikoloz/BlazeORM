import pytest

from blazeorm.core import IntegerField, Model, StringField
from blazeorm.query import Q


class User(Model):
    name = StringField(nullable=False)
    age = IntegerField()


def test_queryset_to_sql_simple_filter():
    qs = User.objects.filter(name="Alice")
    sql, params = qs.to_sql()
    assert sql == 'SELECT "id", "name", "age" FROM "user" WHERE "name" = ?'
    assert params == ["Alice"]


def test_queryset_ordering_and_limit():
    qs = User.objects.filter(age__gte=18).order_by("-age").limit(5)
    sql, params = qs.to_sql()
    assert sql == 'SELECT "id", "name", "age" FROM "user" WHERE "age" >= ? ORDER BY "age" DESC LIMIT 5'
    assert params == [18]


def test_queryset_combined_q_objects():
    qs = User.objects.where(Q(name="Alice") | Q(age__lt=18)).offset(10)
    sql, params = qs.to_sql()
    assert sql == 'SELECT "id", "name", "age" FROM "user" WHERE ("name" = ?) OR ("age" < ?) LIMIT -1 OFFSET 10'
    assert params == ["Alice", 18]


def test_queryset_exclude_negates_expression():
    qs = User.objects.exclude(name="Bob")
    sql, params = qs.to_sql()
    assert sql == 'SELECT "id", "name", "age" FROM "user" WHERE NOT ("name" = ?)'
    assert params == ["Bob"]


def test_queryset_null_equality_generates_is_null():
    qs = User.objects.filter(age=None)
    sql, params = qs.to_sql()
    assert sql == 'SELECT "id", "name", "age" FROM "user" WHERE "age" IS NULL'
    assert params == []


def test_unsupported_lookup_raises():
    qs = User.objects.filter(name__startswith="A")
    with pytest.raises(ValueError):
        qs.to_sql()
