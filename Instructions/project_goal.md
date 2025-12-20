# Project Goal

BlazeORM is a synchronous, modular Python ORM for SQLite, PostgreSQL, and MySQL that emphasizes readability, explicit architecture (models → query → session → adapter → dialect), safe migrations, eager loading, caching, hooks, and performance visibility.

## Mission
- Provide declarative models and relationships that compile to dialect-aware SQL.
- Offer session-driven persistence with transactions, identity map, unit-of-work, caching, hooks, and eager loading to avoid N+1.
- Deliver schema/migration helpers with destructive-operation safeguards.
- Ship adapters/dialects with DSN parsing, redaction, and parameter validation for the supported databases.
- Include performance tracking and example apps/tests to demonstrate correct usage.

## Target Users
- Python developers needing a lightweight, inspectable ORM across SQLite/Postgres/MySQL.
- Contributors extending adapters, performance, or schema capabilities while keeping the architecture intact.
- Automated agents running example apps/tests as reference implementations.

## What This Project Is Not
- Not asynchronous (no async/await; synchronous DB-API only).
- Not an admin UI/CLI generator or full Django clone.
- Not an implicit auto-migration tool; migrations are explicit.
- Not a schema diff/inspection engine.
- Not an ORM that bypasses adapters/dialects for raw connections.
