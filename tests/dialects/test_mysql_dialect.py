from blazeorm.dialects import MySQLDialect


def test_mysql_dialect_quotes_identifiers():
    dialect = MySQLDialect()
    assert dialect.quote_identifier("user`name") == "`user``name`"
    assert dialect.format_table("analytics.events") == "`analytics`.`events`"


def test_mysql_limit_clause():
    dialect = MySQLDialect()
    assert dialect.limit_clause(10, None) == "LIMIT 10"
    assert dialect.limit_clause(None, 5) == "LIMIT 18446744073709551615 OFFSET 5"
    assert dialect.limit_clause(10, 5) == "LIMIT 10 OFFSET 5"


def test_mysql_placeholder():
    dialect = MySQLDialect()
    assert dialect.parameter_placeholder() == "%s"
