from blazeorm.dialects import PostgresDialect


def test_postgres_dialect_quotes_identifiers():
    dialect = PostgresDialect()
    assert dialect.quote_identifier('table"name') == '"table""name"'
    assert dialect.format_table("public.users") == '"public"."users"'


def test_postgres_dialect_limit_clause():
    dialect = PostgresDialect()
    assert dialect.limit_clause(10, None) == "LIMIT 10"
    assert dialect.limit_clause(None, 5) == "OFFSET 5"
    assert dialect.limit_clause(10, 5) == "LIMIT 10 OFFSET 5"


def test_postgres_dialect_placeholder():
    dialect = PostgresDialect()
    assert dialect.parameter_placeholder() == "%s"
