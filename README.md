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

## Example Blog App

Explore BlazeORM end-to-end via the sample blog packaged under `examples/blog_app`:

1. Bootstrap and seed the database programmatically:

   ```python
   from examples.blog_app import bootstrap_session, seed_sample_data, fetch_recent_posts

   session = bootstrap_session("sqlite:///blog_example.db")
   seed_sample_data(session)
   print(fetch_recent_posts(session))
   session.close()
   ```

2. Or run the ready-made demo script:

   ```bash
   python -m examples.blog_app.demo
   ```

The example uses the migration engine, sessions, caching/identity map, and secure DSN handling to provide a concise reference implementation you can adapt for your own applications.

## Database Adapters

- **SQLite**: Uses the stdlib `sqlite3` module (default). Ideal for local development or small deployments.
- **PostgreSQL**: Provided via `psycopg`. Instantiate sessions with `PostgresAdapter` and `ConnectionConfig.from_dsn`.
- **MySQL**: Provided via `PyMySQL` or `mysqlclient`. Instantiate sessions with `MySQLAdapter` and `ConnectionConfig.from_dsn`.


## Performance Monitoring & N+1 Detection

- Every `Session.execute` call is timed with structured logs and summarized through the new performance tracker (`Session.query_stats()`).
- Potential N+1 patterns are detected automatically: if the same SQL runs repeatedly with different parameters (default threshold: 5 executions), BlazeORM emits a warning from `blazeorm.persistence.session`.
- Configure sensitivity by passing `performance_threshold=` when constructing a session, or inspect collected metrics to spot hotspots programmatically.
