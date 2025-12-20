# Constraints (Non-Negotiable)
- Synchronous only; no async APIs.
- All SQL execution must go through adapters with dialect-aware placeholders; no raw driver calls.
- Migrations are explicit via `MigrationEngine`/`SchemaBuilder`; no implicit schema diffs or auto-migrate.
- Destructive operations require explicit confirmation (`force=True` when marked destructive).
- Session-bound ORM usage: QuerySet iteration and m2m managers require an active `Session` (contextvar or explicit binding).
- Dialect correctness: quoting, placeholders, and limit/offset must use the active dialect; never hard-code SQLite syntax in shared paths.
- Security: DSNs must be parsed via `ConnectionConfig.from_dsn/from_env` and redacted in logs; secrets must not be logged.
- Validation: adapters must enforce parameter counts; persistence must run `full_clean` before save.
- Transactions: use `TransactionManager` via `Session`; respect savepoint capability flags.
