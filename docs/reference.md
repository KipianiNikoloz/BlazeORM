# BlazeORM Reference

## Models and Fields

`Model` classes collect ordered fields and attach an `objects` query manager. Supported scalar fields are `AutoField`, `IntegerField`, `FloatField`, `BooleanField`, `StringField`, and `DateTimeField`. Fields support primary keys, uniqueness, nullability, Python/database defaults, indexes, choices, validators, custom columns, and help text. `DateTimeField(auto_now_add=True)` assigns an aware UTC creation timestamp on insert; `auto_now=True` assigns one on insert and every update. ISO-formatted database values hydrate as `datetime` objects.

`Model.full_clean()` runs field validation and the model's `clean()` hook. Instances expose `pk`, `to_dict()`, dirty tracking, lifecycle hook registration, and many-to-many mutation helpers. `save(session=None)` inserts new instances or updates Session-loaded instances; `delete(session=None)` removes persisted instances. Both accept an explicit Session or use the current session context.

Models with `Meta.abstract = True` contribute cloned scalar and relationship fields to abstract and concrete descendants without receiving an automatic primary key themselves. Concrete descendants get an automatic key only when no inherited or declared key exists. Subclass declarations override inherited names; ambiguous names from multiple abstract bases require an explicit override. Concrete multi-table inheritance is not supported.

## Relationships

`ForeignKey`, `OneToOneField`, and `ManyToManyField` install forward descriptors and reverse accessors. Reverse names default to `<model>_set`. Many-to-many managers support `all`, `add`, `remove`, and `clear` inside an active session.

## Queries

`Q` objects combine filters with `&`, `|`, and `~`. QuerySets support `filter`, `exclude`, `where`, `order_by`, `limit`, `offset`, `select_related`, `prefetch_related`, SQL compilation, and session-bound iteration. `first()` returns one row or `None`; `get()` enforces exactly one row with `DoesNotExist` and `MultipleObjectsReturned`; `count()` and `exists()` use database-side terminal queries. `values(*fields)` returns dictionaries keyed by model field name, while `values_list(*fields, flat=False)` returns positional tuples or flat scalars for one field. Projections preserve filtering, ordering, and slicing but intentionally skip model hydration and eager loading. The default model manager delegates the same operations through the active session.

Supported scalar lookups are `exact`, `iexact`, `gt`, `gte`, `lt`, `lte`, `contains`, `icontains`, `startswith`, `endswith`, `in`, and `isnull`. Empty `in` collections match nothing; invalid collection, boolean, and text values raise explicit errors. Case-insensitive matching uses `LOWER` for consistent behavior across supported databases. SQL and parameters are returned separately and placeholders come from the active dialect.

## Sessions and Persistence

`Session` owns the connection boundary, transactions, identity map, unit of work, cache, hooks, and performance tracker. Construct it with an adapter and either a `ConnectionConfig` or DSN. Use `with session:` to bind manager and relationship operations to the current context.

New, dirty, and deleted instances flow through the unit of work. Commits validate and persist changes; rollbacks restore tracked state. Nested transactions use savepoints when supported.

Instance methods delegate to this same unit of work, so validation, hooks, identity maps, caches, transactions, and backend dialect behavior remain centralized in Session. Application-assigned primary keys do not make a newly constructed model persisted; its first `save()` still inserts it. Autocommit sessions commit inserts, updates, and deletes immediately.

`Session.get()` fetches by one field and reuses identity-map and second-level cache entries for primary-key lookups. `Session.query()` returns a session-bound QuerySet. Many-to-many helpers update through tables and invalidate related caches.

`Session.refresh(instance)` bypasses caches and reloads every scalar field by primary key into the same Python object. It discards pending local scalar changes, clears relation caches, updates identity and second-level caches, and raises `DoesNotExist` if the row has disappeared.

## Adapters and Dialects

SQLite, PostgreSQL, and MySQL adapters share connection, execution, transaction, parameter-validation, redaction, and slow-query behavior. `ConnectionConfig` parses DSNs and options including autocommit, isolation, timeouts, and backend SSL settings. Adapter failures use configuration, connection, execution, and transaction exception categories.

Dialects provide identifier quoting, table formatting, limit/offset rendering, placeholders, column definitions, and capability flags.

## Schema and Migrations

`SchemaBuilder` renders tables, foreign keys, many-to-many through tables, and indexes. `MigrationEngine.apply()` runs ordered `MigrationOperation` values and records versions. Destructive operations require explicit confirmation.

## Hooks, Caching, and Observability

Lifecycle events are `before_validate`, `after_validate`, `before_save`, `after_save`, `before_delete`, `after_delete`, and `after_commit`. Handlers may be global or model-specific.

Sessions accept no-op or in-memory cache backends. Structured logging supports correlation IDs and redacts sensitive values. `PerformanceTracker` records SQL timings, warns about repeated-query/N+1 patterns, and exports or resets statistics. Slow-query thresholds come from `BLAZE_SLOW_QUERY_MS` or adapter/session overrides.

## Examples and Tests

The blog example demonstrates schema setup, persistence, eager loading, and performance tracking. The library example emphasizes many-to-many mutation and eager loading. Their executable flows are covered under `tests/examples/`.
