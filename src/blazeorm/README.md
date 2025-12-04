BlazeORM Package
================

This document summarizes the purpose and surface of the core BlazeORM package. The package is organized into focused submodules; each submodule has its own README for deeper details.

Overview
--------
- Declarative models with typed fields and relationships.
- Strategy-based dialects and database adapters (SQLite, Postgres, MySQL).
- Query builder + eager-loading (`select_related`, `prefetch_related`) with execution on `Session`.
- Persistence layer with transactions, unit-of-work, identity map, hooks, caching, and performance tracking.
- Schema builder + migration engine with safety checks.
- Security utilities for DSN parsing/redaction and destructive operation confirmation.
- Examples and test suites demonstrating end-to-end usage.

Key Modules
-----------
- `core/` — Model metaclass, fields, relations, and registry.
- `query/` — `Q` expressions, SQL compiler, `QuerySet` and managers.
- `persistence/` — `Session`, UoW, IdentityMap, transactions, caches, hooks integration.
- `adapters/` — Database adapters and `ConnectionConfig`.
- `dialects/` — Dialect abstractions and implementations for SQLite/Postgres/MySQL.
- `schema/` — Schema builder and migration engine.
- `security/` — DSN utilities and destructive operation confirmation.
- `cache/` — Cache backend protocol and in-memory implementation.
- `hooks/` — Hook dispatcher and registration helpers.
- `utils/` — Logging, performance tracking, naming utilities.
- `examples/` — Reference application and demos.

Quick Start (High Level)
------------------------
1. Define models under `core` using fields and relationships.
2. Create a `Session` with an adapter (`SQLiteAdapter`, `PostgresAdapter`, `MySQLAdapter`) and optional DSN via `ConnectionConfig`.
3. Run queries with `session.query(Model)` or within `with session:` to reuse the same transaction/connection and identity map.
4. Use `select_related`/`prefetch_related` to avoid N+1 queries (including nested and many-to-many paths).
5. Apply schema changes via `schema.MigrationEngine` using SQL from `schema.SchemaBuilder`.
6. Observe/log performance using `Session.query_stats()` and structured logging utilities.

Testing & Compliance
--------------------
- Codebase targets Python 3.9+ and is kept black/ruff/isort/mypy/pytest friendly.
- Tests under `tests/` exercise all modules, including adapters, query execution, persistence, schema, security, caching, hooks, performance, and examples.

