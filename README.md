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

BlazeORM enforces parameterized queries and offers DSN parsing helpers. Use `blazeorm.security.dsns.parse_dsn` to safely handle connection strings and `confirm_destructive_operation` to guard dangerous migration steps.
