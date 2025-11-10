# BlazeORM

Simple and lightweight ORM built in Python utilising SQLite.

## Logging

BlazeORM ships with structured logging helpers. Enable them at startup:

```python
from blazeorm import configure_logging

configure_logging()
```

Every query executed through the session or adapters emits timing information with a correlation ID so you can trace slow statements quickly. Use `blazeorm.get_logger` for custom components to participate in the same logging pipeline.

## Security

BlazeORM enforces parameterized queries and integrates DSN utilities across adapters, sessions, and schema tooling.

### DSN handling

- Build safe connection configs with `ConnectionConfig.from_dsn("postgres://...")` or `ConnectionConfig.from_env("DATABASE_URL")`. DSN credentials are automatically redacted in logs.
- Sessions can now be created directly from a DSN: `Session(SQLiteAdapter(), dsn="sqlite:///example.db")`.
- Use `blazeorm.security.dsns.parse_dsn` for manual parsing needs or redaction helpers.

### Migration safety

- Generating destructive schema statements (for example, `SchemaBuilder.drop_table_sql`) emits warnings.
- `MigrationEngine` logs every destructive operation and requires `force=True` to proceed, delegating to `confirm_destructive_operation`.

### Secure parameter handling

- All adapters validate placeholder counts before dispatching SQL and ensure parameterized execution.
- Logged parameters are redacted when they appear to contain secrets (e.g., strings including `password`).
