SQL Dialects
============

What Lives Here
---------------
- `base.py`: Dialect interface for quoting identifiers, rendering limit/offset, column definitions, parameter placeholders.
- `sqlite.py`: SQLite-specific quoting and limit/offset.
- `postgres.py`: PostgreSQL dialect specifics (`%s` placeholders, quoting).
- `mysql.py`: MySQL dialect specifics and limit/offset syntax.

Key Behaviors
-------------
- Dialects provide `quote_identifier`, `format_table`, `limit_clause`, `parameter_placeholder`, and column rendering helpers used by schema builder and SQL compiler.
- Limit/offset rendering is dialect-aware; compiler defers to the dialect.

Testing References
------------------
- `tests/dialects/test_sqlite.py`, `tests/dialects/test_postgres_dialect.py`, `tests/dialects/test_mysql_dialect.py`.

