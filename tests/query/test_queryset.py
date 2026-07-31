import pytest

from blazeorm.core import ForeignKey, IntegerField, Model, StringField
from blazeorm.dialects import MySQLDialect, PostgresDialect, SQLiteDialect
from blazeorm.query import Q, QuerySet


class User(Model):
    name = StringField(nullable=False)
    age = IntegerField()


class Post(Model):
    title = StringField()
    author = ForeignKey(User, related_name="posts")


def test_queryset_to_sql_simple_filter():
    qs = User.objects.filter(name="Alice")
    sql, params = qs.to_sql()
    assert sql == 'SELECT "user"."id", "user"."name", "user"."age" FROM "user" WHERE "name" = ?'
    assert params == ["Alice"]


def test_queryset_ordering_and_limit():
    qs = User.objects.filter(age__gte=18).order_by("-age").limit(5)
    sql, params = qs.to_sql()
    assert (
        sql
        == 'SELECT "user"."id", "user"."name", "user"."age" FROM "user" WHERE "age" >= ? ORDER BY "age" DESC LIMIT 5'
    )
    assert params == [18]


def test_queryset_combined_q_objects():
    qs = User.objects.where(Q(name="Alice") | Q(age__lt=18)).offset(10)
    sql, params = qs.to_sql()
    assert (
        sql
        == 'SELECT "user"."id", "user"."name", "user"."age" FROM "user" WHERE ("name" = ?) OR ("age" < ?) LIMIT -1 OFFSET 10'
    )
    assert params == ["Alice", 18]


def test_queryset_exclude_negates_expression():
    qs = User.objects.exclude(name="Bob")
    sql, params = qs.to_sql()
    assert (
        sql == 'SELECT "user"."id", "user"."name", "user"."age" FROM "user" WHERE NOT ("name" = ?)'
    )
    assert params == ["Bob"]


def test_queryset_null_equality_generates_is_null():
    qs = User.objects.filter(age=None)
    sql, params = qs.to_sql()
    assert sql == 'SELECT "user"."id", "user"."name", "user"."age" FROM "user" WHERE "age" IS NULL'
    assert params == []


def test_unsupported_lookup_raises():
    qs = User.objects.filter(name__regex="^A")
    with pytest.raises(ValueError, match="Unsupported lookup 'regex'"):
        qs.to_sql()


@pytest.mark.parametrize(
    ("lookup", "value", "fragment", "params"),
    [
        ("age__in", [18, 21], '"age" IN (?, ?)', [18, 21]),
        ("age__in", [], "1 = 0", []),
        ("age__isnull", True, '"age" IS NULL', []),
        ("age__isnull", False, '"age" IS NOT NULL', []),
    ],
)
def test_collection_and_null_lookups(lookup, value, fragment, params):
    sql, actual_params = User.objects.filter(**{lookup: value}).to_sql()
    assert fragment in sql
    assert actual_params == params


@pytest.mark.parametrize("value", ["abc", b"abc", 42])
def test_in_lookup_rejects_non_collection_values(value):
    with pytest.raises(ValueError, match="'in' lookup requires a non-string iterable"):
        User.objects.filter(age__in=value).to_sql()


def test_isnull_lookup_requires_boolean():
    with pytest.raises(ValueError, match="'isnull' lookup requires a boolean"):
        User.objects.filter(age__isnull=1).to_sql()


@pytest.mark.parametrize(
    ("lookup", "value", "fragment", "params"),
    [
        ("name__startswith", "Al", '"name" LIKE ?', ["Al%"]),
        ("name__endswith", "ice", '"name" LIKE ?', ["%ice"]),
        ("name__iexact", "ALICE", 'LOWER("name") = ?', ["alice"]),
        ("name__icontains", "LI", 'LOWER("name") LIKE ?', ["%li%"]),
    ],
)
def test_text_lookups(lookup, value, fragment, params):
    sql, actual_params = User.objects.filter(**{lookup: value}).to_sql()
    assert fragment in sql
    assert actual_params == params


@pytest.mark.parametrize("lookup", ["startswith", "endswith", "contains", "iexact", "icontains"])
def test_text_lookups_reject_non_string_values(lookup):
    with pytest.raises(ValueError, match=f"'{lookup}' lookup requires a string"):
        User.objects.filter(**{f"name__{lookup}": 12}).to_sql()


@pytest.mark.parametrize(
    ("dialect", "quoted_column", "placeholder"),
    [
        (SQLiteDialect(), '"name"', "?"),
        (PostgresDialect(), '"name"', "%s"),
        (MySQLDialect(), "`name`", "%s"),
    ],
)
def test_case_insensitive_lookup_uses_active_dialect(dialect, quoted_column, placeholder):
    sql, params = QuerySet(User, dialect=dialect).filter(name__icontains="AL").to_sql()
    assert f"LOWER({quoted_column}) LIKE {placeholder}" in sql
    assert params == ["%al%"]


@pytest.mark.parametrize(
    ("dialect", "table", "placeholder"),
    [
        (SQLiteDialect(), '"user"', "?"),
        (PostgresDialect(), '"user"', "%s"),
        (MySQLDialect(), "`user`", "%s"),
    ],
)
def test_terminal_compilers_use_portable_sliced_probes(dialect, table, placeholder):
    queryset = QuerySet(User, dialect=dialect).filter(age__gte=18).offset(1).limit(2)
    compiler = queryset._compiler()

    count_sql, count_params = compiler.compile_count()
    exists_sql, exists_params = compiler.compile_exists()

    assert count_sql == (
        f"SELECT COUNT(*) FROM (SELECT 1 FROM {table} WHERE "
        f"{dialect.quote_identifier('age')} >= {placeholder} "
        f"{dialect.limit_clause(2, 1)}) AS blaze_count"
    )
    assert exists_sql == (
        f"SELECT 1 FROM {table} WHERE {dialect.quote_identifier('age')} >= {placeholder} "
        f"{dialect.limit_clause(1, 1)}"
    )
    assert count_params == exists_params == [18]


@pytest.mark.parametrize(
    ("dialect", "table", "name_column", "age_column", "placeholder"),
    [
        (SQLiteDialect(), '"user"', '"name"', '"age"', "?"),
        (PostgresDialect(), '"user"', '"name"', '"age"', "%s"),
        (MySQLDialect(), "`user`", "`name`", "`age`", "%s"),
    ],
)
def test_projection_compiler_selects_requested_fields_and_preserves_query(
    dialect, table, name_column, age_column, placeholder
):
    compiler = (
        QuerySet(User, dialect=dialect)
        .filter(age__gte=18)
        .order_by("-age")
        .offset(1)
        .limit(2)
        ._compiler()
    )

    sql, params = compiler.compile_projection(("name", "age"))

    assert sql == (
        f"SELECT {table}.{name_column}, {table}.{age_column} FROM {table} "
        f"WHERE {age_column} >= {placeholder} ORDER BY {age_column} DESC "
        f"{dialect.limit_clause(2, 1)}"
    )
    assert params == [18]


def test_projection_compiler_rejects_unknown_field():
    compiler = QuerySet(User)._compiler()

    with pytest.raises(KeyError, match="Unknown field 'missing'"):
        compiler.compile_projection(("missing",))


@pytest.mark.parametrize("dialect", [SQLiteDialect(), PostgresDialect(), MySQLDialect()])
def test_aggregate_compiler_preserves_ordered_slice(dialect):
    compiler = (
        QuerySet(User, dialect=dialect)
        .filter(age__gte=18)
        .order_by("-age")
        .offset(1)
        .limit(2)
        ._compiler()
    )
    table = dialect.format_table("user")
    age = dialect.quote_identifier("age")
    placeholder = dialect.parameter_placeholder()
    value_alias = dialect.quote_identifier("blaze_value")
    aggregate_alias = dialect.quote_identifier("blaze_aggregate")

    sql, params = compiler.compile_aggregate("SUM", "age")

    assert sql == (
        f"SELECT SUM({value_alias}) FROM (SELECT {table}.{age} AS {value_alias} "
        f"FROM {table} WHERE {age} >= {placeholder} ORDER BY {age} DESC "
        f"{dialect.limit_clause(2, 1)}) AS {aggregate_alias}"
    )
    assert params == [18]


def test_aggregate_compiler_rejects_invalid_function_and_field():
    compiler = QuerySet(User)._compiler()

    with pytest.raises(ValueError, match="Unsupported aggregate"):
        compiler.compile_aggregate("MEDIAN", "age")
    with pytest.raises(ValueError, match="numeric field"):
        compiler.compile_aggregate("MAX", "name")


@pytest.mark.parametrize("dialect", [SQLiteDialect(), PostgresDialect(), MySQLDialect()])
def test_bulk_mutation_compiler_uses_dialect_and_filter(dialect):
    compiler = QuerySet(User, dialect=dialect).filter(age__lt=18)._compiler()
    table = dialect.format_table("user")
    name = dialect.quote_identifier("name")
    age = dialect.quote_identifier("age")
    placeholder = dialect.parameter_placeholder()

    update_sql, update_params = compiler.compile_update({"name": "Minor"})
    delete_sql, delete_params = compiler.compile_delete()

    assert update_sql == f"UPDATE {table} SET {name} = {placeholder} WHERE {age} < {placeholder}"
    assert update_params == ["Minor", 18]
    assert delete_sql == f"DELETE FROM {table} WHERE {age} < {placeholder}"
    assert delete_params == [18]


@pytest.mark.parametrize(
    "query",
    [
        QuerySet(User),
        QuerySet(User).filter(age=20).order_by("name"),
        QuerySet(User).filter(age=20).limit(1),
        QuerySet(User).filter(age=20).offset(1),
        QuerySet(Post).filter(title="x").select_related("author"),
        QuerySet(User).filter(age=20).prefetch_related("posts"),
    ],
)
def test_bulk_mutation_compiler_rejects_unsafe_query_shapes(query):
    with pytest.raises(ValueError, match="Bulk mutation"):
        query._compiler().compile_delete()


def test_bulk_update_compiler_validates_values_and_primary_key():
    compiler = QuerySet(User).filter(name="Alice")._compiler()

    with pytest.raises(ValueError, match="at least one field"):
        compiler.compile_update({})
    with pytest.raises(KeyError, match="Unknown field 'missing'"):
        compiler.compile_update({"missing": 1})
    with pytest.raises(ValueError, match="primary key"):
        compiler.compile_update({"id": 2})


def test_query_errors_are_publicly_exported():
    from blazeorm import DoesNotExist as RootDoesNotExist
    from blazeorm import MultipleObjectsReturned as RootMultipleObjectsReturned
    from blazeorm import QueryError as RootQueryError
    from blazeorm.query import DoesNotExist, MultipleObjectsReturned, QueryError

    assert RootQueryError is QueryError
    assert RootDoesNotExist is DoesNotExist
    assert RootMultipleObjectsReturned is MultipleObjectsReturned


def test_select_related_generates_join():
    qs = Post.objects.select_related("author")
    sql, params = qs.to_sql()
    assert 'LEFT JOIN "user" ON "post"."author" = "user"."id"' in sql
    assert '"author__name"' in sql
    assert params == []


def test_prefetch_related_records_fields():
    qs = User.objects.prefetch_related("posts", "articles")
    assert qs._prefetch_related == ("posts", "articles")
