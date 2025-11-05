from blazeorm.dialects import SQLiteDialect


def test_sqlite_identifier_quoting():
    dialect = SQLiteDialect()
    assert dialect.quote_identifier("table") == '"table"'
    assert dialect.quote_identifier('bad"name') == '"bad""name"'


def test_sqlite_limit_clause():
    dialect = SQLiteDialect()
    assert dialect.limit_clause(10, None) == "LIMIT 10"
    assert dialect.limit_clause(10, 5) == "LIMIT 10 OFFSET 5"
    assert dialect.limit_clause(None, 5) == "LIMIT -1 OFFSET 5"


def test_sqlite_column_definition():
    dialect = SQLiteDialect()
    rendered = dialect.render_column_definition("name", "TEXT", nullable=False)
    assert rendered == '"name" TEXT NOT NULL'
