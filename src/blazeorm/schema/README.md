Schema Builder and Migration Engine
===================================

What Lives Here
---------------
- `builder.py`: Converts model metadata to DDL SQL (tables, m2m join tables).
- `migration.py`: Migration engine applying operations with version tracking and destructive-op confirmation.

Key Behaviors
-------------
- `SchemaBuilder.create_table_sql(model)`: Renders CREATE TABLE with proper columns, PK/unique/defaults, and FK constraints via dialect.
- `create_many_to_many_sql(model)`: Renders join tables for M2M fields (deduplicated) with FK constraints.
- `create_index_sql(model)`: Renders CREATE INDEX statements for fields with `index=True`.
- `drop_index_sql(model)`: Renders DROP INDEX statements with warnings for destructive operations.
- `MigrationEngine.apply(app, version, ops)`: Applies operations with adapter/dialect and records version, warning on destructive operations (confirmation required by higher layers).
- Logs warnings for DROP generation to encourage manual confirmation.

Usage Notes
-----------
- Integrate builder output into migration operations (`MigrationOperation(sql=...)`) and run via `MigrationEngine`.
- Join-table generation respects field-specific db_table overrides and remote PK column names.

Testing References
------------------
- `tests/schema/test_schema_builder.py`, `tests/schema/test_migration_engine.py`, `tests/security/test_security.py` (destructive confirmation).
