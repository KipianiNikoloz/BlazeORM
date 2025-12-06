# BlazeORM

Modular Python ORM with eager loading, migrations, security hardening, caching, performance tracking, and multi-database adapters (SQLite, PostgreSQL, MySQL).

## Elevator Pitch
- Declarative models, typed fields, and relationships (FK/O2O/M2M) with forward/reverse accessors.
- Query builder + execution with `select_related` / `prefetch_related` (nested, m2m-aware) to eliminate N+1 queries.
- Persistence layer with transactions, unit-of-work, identity map, caching, hooks, and performance tracker.
- Strategy-based dialects and adapters with DSN parsing, redaction, parameter validation, and structured logging.
- Schema builder + migration engine with destructive-operation safeguards.
- Example app and comprehensive tests to guide usage.

## Architecture
- `src/blazeorm/core`: Models, fields, relations, registry, validation hooks.
- `src/blazeorm/query`: `Q` expressions, SQL compiler, `QuerySet`, managers, eager loading.
- `src/blazeorm/persistence`: `Session`, identity map, UoW, transactions/savepoints, caching, hooks, m2m helpers.
- `src/blazeorm/adapters`: SQLite/Postgres/MySQL adapters, `ConnectionConfig` (DSN/env parsing, redaction).
- `src/blazeorm/dialects`: Quoting, limit/offset, placeholders per backend.
- `src/blazeorm/schema`: Schema builder, migration engine, destructive confirmations.
- `src/blazeorm/security`: DSN utilities and migration safety helpers.
- `src/blazeorm/cache`, `src/blazeorm/hooks`, `src/blazeorm/utils`: Caching backends, lifecycle hooks, logging, performance tracker.
- `examples/`: Blog app showing migrations, sessions, seeding, and querying.
- Each subpackage has a README for deeper details.

## Quickstart
```python
from blazeorm.adapters import SQLiteAdapter, ConnectionConfig
from blazeorm.persistence import Session
from mymodels import User

session = Session(SQLiteAdapter(), connection_config=ConnectionConfig.from_dsn("sqlite:///app.db"))
with session:
    users = list(session.query(User).prefetch_related("groups").order_by("id"))
    for u in users:
        print(u.id, u.name, [g.name for g in u.groups])
```

### Defining Models
```python
from blazeorm.core import Model, StringField, ForeignKey, ManyToManyField

class Author(Model):
    name = StringField(nullable=False)

class Category(Model):
    name = StringField(nullable=False)

class Article(Model):
    title = StringField()
    author = ForeignKey(Author, related_name="articles")
    categories = ManyToManyField(Category, related_name="articles")
```

### Schema & Migrations
```python
from blazeorm.schema import SchemaBuilder, MigrationEngine, MigrationOperation
from blazeorm.dialects import SQLiteDialect

builder = SchemaBuilder(SQLiteDialect())
ops = [MigrationOperation(sql=builder.create_table_sql(Article))]
ops += [MigrationOperation(sql=stmt) for stmt in builder.create_many_to_many_sql(Article)]
engine = MigrationEngine(session.adapter, session.dialect)
engine.apply("blog", "0001", ops)
```

### Eager Loading
- `select_related("author")` for join-based eager loading of FK/O2O.
- `prefetch_related("categories", "author__articles")` for bulk loading m2m and nested relations.
- Empty relations return empty lists; identity map/caches are reused during iteration.

### Transactions, Hooks, and M2M Helpers
- Use `with session:` or `session.transaction()` for transactional scopes.
- Hooks: `before/after_validate`, `before/after_save`, `before/after_delete`, `after_commit` fired by `Session`.
- Many-to-many helpers: `Session.add_m2m/remove_m2m/clear_m2m` and `Model.m2m_add/remove/clear` manage join rows and cache invalidation.

### Security
- DSN parsing/redaction via `ConnectionConfig.from_dsn/from_env`; credentials are redacted in logs.
- Adapters validate placeholder counts; parameters are redacted when they appear sensitive.
- Migration engine logs destructive ops; `SchemaBuilder.drop_table_sql` warns loudly.

### Performance & Observability
- Structured logging with correlation IDs via `blazeorm.utils.logging.configure_logging`.
- `PerformanceTracker` records SQL timings and warns on N+1 patterns; inspect with `Session.query_stats()`.

### Example Blog App
- Located in `examples/blog_app`.
- Run `python -m examples.blog_app.demo` or import `bootstrap_session` / `seed_sample_data`.
- Additional library demo in `examples/library_app` showcasing many-to-many (writers/books/genres) with eager loading.

## Installation
- From source: `pip install .`
- With optional extras: `pip install .[postgres]` or `pip install .[mysql]` to pull driver dependencies.
- PyPI publishing is planned; once available, installation will be `pip install blazeorm`.

## CI & Quality
- GitHub Actions run pytest plus ruff/black/isort/mypy checks.
- Note: mypy is currently configured to ignore type errors pending a full typing pass.
- Integration tests for Postgres/MySQL run when `BLAZE_POSTGRES_DSN` / `BLAZE_MYSQL_DSN` are provided and drivers are installed; otherwise they skip.

## Testing
- Run the suite: `python -m pytest`
- Tests cover adapters, dialects, core models/relations, query compilation/execution, persistence, schema, security, caching, hooks, performance, and examples.

## Further Reading
- `src/blazeorm/README.md` for package overview.
- Module READMEs under each subpackage for focused details (core, query, persistence, adapters, schema, security, cache, hooks, utils, examples).
