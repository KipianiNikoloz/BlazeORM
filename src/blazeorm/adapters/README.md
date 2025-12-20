Database Adapters & ConnectionConfig
====================================

What Lives Here
---------------
- `base.py`: Adapter protocol, `ConnectionConfig` (DSN/env parsing, redaction, autocommit, isolation, options), shared validation hooks.
- `sqlite.py`: SQLite adapter with parameter count validation, transaction helpers, row factory setup, and DSN-aware logging.
- `postgres.py`: Postgres adapter (psycopg), connection/state management with reconnect on closed connections, autocommit-aware begin, parameter validation.
- `mysql.py`: MySQL adapter using PyMySQL/mysqlclient with DSN logging and parameter validation.

Key Behaviors
-------------
- All adapters expose `connect/close/execute/executemany/begin/commit/rollback/last_insert_id`.
- Parameter validation ensures placeholder counts match supplied params.
- ConnectionConfig:
  - `from_dsn/from_env` parse URLs, redact secrets in logs, apply timeouts/options/SSL settings, and provide descriptive labels.
  - `descriptive_label` is used for structured connection logging.
- Adapters raise consistent exceptions for configuration, connection, execution, and transaction failures.
- SQLite adapter guards nested transactions and enforces parameter count.
- Postgres adapter reconnects when connection is closed and skips `BEGIN` if autocommit is enabled.

Usage Notes
-----------
- Prefer `ConnectionConfig.from_dsn` to configure adapters; pass into `Session`.
- Autocommit is optional; transactions are managed by `Session` and adapters.
- Secrets are redacted automatically in logs via ConnectionConfig and adapter `_redact`.
- DSN query parameters can supply `autocommit`, `timeout`, `isolation_level`, `connect_timeout`, and SSL-related options (e.g., `sslmode`, `sslrootcert`, `ssl_ca`).

Testing References
------------------
- `tests/adapters/test_sqlite_adapter.py`, `tests/adapters/test_postgres_adapter.py`, `tests/adapters/test_mysql_adapter.py`, `tests/security/test_security.py`.
