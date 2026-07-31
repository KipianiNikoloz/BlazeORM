"""
Session management coordinating adapters, unit of work, and identity map.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Iterable, Optional, Type

from ..adapters.base import ConnectionConfig, Cursor, DatabaseAdapter
from ..cache import CacheBackend, NoOpCache
from ..core.model import Model
from ..core.relations import ManyToManyField, relation_registry
from ..dialects.base import Dialect
from ..dialects.sqlite import SQLiteDialect
from ..security.redaction import redact_params
from ..utils import PerformanceTracker, get_logger, time_call
from ..utils.performance import resolve_slow_query_ms
from .identity_map import IdentityMap
from .transaction import TransactionManager
from .unit_of_work import UnitOfWork

_current_session: ContextVar["Session | None"] = ContextVar(
    "blazeorm_current_session", default=None
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _ModelState:
    field_values: dict[str, Any]
    initial_state: dict[str, Any]
    related_cache: dict[str, Any]
    persisted: bool


@dataclass
class _SessionSnapshot:
    new: set[Model]
    dirty: set[Model]
    deleted: set[Model]
    model_states: dict[Model, _ModelState]
    identity_instances: set[Model]


class Session:
    """
    Coordinates persistence operations for a set of model instances.
    """

    def __init__(
        self,
        adapter: DatabaseAdapter,
        *,
        connection_config: Optional[ConnectionConfig] = None,
        dsn: str | None = None,
        autocommit: bool = False,
        cache_backend: Optional[CacheBackend] = None,
        performance_threshold: int = 5,
        slow_query_ms: int | None = None,
    ) -> None:
        self.adapter = adapter
        self.autocommit = autocommit
        self.dialect: Dialect = adapter.dialect if hasattr(adapter, "dialect") else SQLiteDialect()
        if connection_config and dsn:
            raise ValueError("Provide either connection_config or dsn, not both.")
        if dsn and not connection_config:
            connection_config = ConnectionConfig.from_dsn(dsn)
        self.connection_config = connection_config or ConnectionConfig.from_dsn(
            "sqlite:///:memory:"
        )
        self.identity_map = IdentityMap()
        self.unit_of_work = UnitOfWork()
        self.transaction_manager = TransactionManager(adapter, self.dialect)
        self._lock = RLock()
        self._uow_snapshots: list[_SessionSnapshot] = []
        self.cache = cache_backend or NoOpCache()
        from ..hooks import hooks

        self.hooks = hooks
        self.logger = get_logger("persistence.session")
        self.slow_query_ms = resolve_slow_query_ms(default=200, override=slow_query_ms)
        self.performance = PerformanceTracker(
            self.logger, n_plus_one_threshold=performance_threshold
        )
        self._ctx_token: Token["Session | None"] | None = None
        self.adapter.connect(self.connection_config)

    # ------------------------------------------------------------------ #
    # Context management
    # ------------------------------------------------------------------ #
    def __enter__(self) -> "Session":
        self.begin()
        self._ctx_token = _current_session.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            if self._ctx_token:
                _current_session.reset(self._ctx_token)
                self._ctx_token = None
            self.close()

    # ------------------------------------------------------------------ #
    def begin(self) -> None:
        with self._lock:
            self._ensure_adapter_connected()
            self.transaction_manager.begin()
            self._snapshot_uow()

    def commit(self) -> None:
        with self._lock:
            if self.transaction_manager.depth == 0:
                self.begin()
            self.flush()
            self.transaction_manager.commit()
            self._discard_uow_snapshot()
            if self.transaction_manager.depth == 0:
                self.unit_of_work.clear()
                self.hooks.fire("after_commit", None, session=self)

    def rollback(self) -> None:
        with self._lock:
            self.transaction_manager.rollback()
            self._restore_uow_snapshot()

    def close(self) -> None:
        with self._lock:
            self.adapter.close()
            self.identity_map.clear()
            self._uow_snapshots.clear()
            self.performance.reset()

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    def add(self, instance: Model) -> None:
        with self._lock:
            self._capture_transaction_participant(instance)
            self.unit_of_work.register_new(instance)
            if self.autocommit:
                self.commit()

    def delete(self, instance: Model) -> None:
        with self._lock:
            self._capture_transaction_participant(instance)
            self.unit_of_work.register_deleted(instance)
            if self.autocommit:
                self.commit()

    def mark_dirty(self, instance: Model) -> None:
        with self._lock:
            self._capture_transaction_participant(instance)
            self.unit_of_work.register_dirty(instance)
            if self.autocommit:
                self.commit()

    def bulk_create(self, instances: Iterable[Model]) -> list[Model]:
        created = list(instances)
        if not created:
            return []
        model = self._validate_bulk_create_instances(created)
        if model._meta.abstract:
            raise ValueError("Session.bulk_create requires a concrete model.")
        snapshots = [
            (
                instance,
                dict(instance._field_values),
                dict(instance._initial_state),
                dict(instance._related_cache),
                instance._persisted,
            )
            for instance in created
        ]
        try:
            with self.transaction():
                for instance in created:
                    self._capture_transaction_participant(instance)
                    self._persist_new(instance)
        except Exception:
            for instance, field_values, initial_state, related_cache, persisted in snapshots:
                self.identity_map.remove(instance)
                self._invalidate_cache(instance)
                instance._field_values = field_values
                instance._initial_state = initial_state
                instance._related_cache = related_cache
                instance._persisted = persisted
            raise
        return created

    @staticmethod
    def _validate_bulk_create_instances(instances: list[Model]) -> type[Model]:
        first = instances[0]
        if not isinstance(first, Model):
            raise TypeError("Session.bulk_create requires Model instances.")
        model = first.__class__
        seen: set[int] = set()
        for instance in instances:
            if not isinstance(instance, Model):
                raise TypeError("Session.bulk_create requires Model instances.")
            if instance.__class__ is not model:
                raise ValueError("Session.bulk_create requires instances of the same model.")
            identity = id(instance)
            if identity in seen:
                raise ValueError("Session.bulk_create cannot receive the same instance twice.")
            seen.add(identity)
            if instance._persisted:
                raise ValueError("Session.bulk_create cannot create an already persisted instance.")
        return model

    # ------------------------------------------------------------------ #
    def flush(self) -> None:
        with self._lock:
            self.unit_of_work.collect_dirty(self.identity_map.values())
            for instance in list(self.unit_of_work.new):
                self._persist_new(instance)
                self.unit_of_work.new.discard(instance)
            for instance in list(self.unit_of_work.dirty):
                self._persist_dirty(instance)
                self.unit_of_work.dirty.discard(instance)
            for instance in list(self.unit_of_work.deleted):
                self._persist_deleted(instance)
                self.unit_of_work.deleted.discard(instance)

    # ------------------------------------------------------------------ #
    def get(self, model: Type[Model], **filters: Any) -> Optional[Model]:
        with self._lock:
            if len(filters) != 1:
                raise ValueError("Session.get currently supports exactly one filter.")
            field_name, value = next(iter(filters.items()))

            pk_field = model._meta.primary_key
            if pk_field and field_name == pk_field.require_name():
                cached = self.identity_map.get(model, value)
                if cached is not None:
                    return cached
                cached_payload = self.cache.get(model, value)
                if cached_payload is not None:
                    instance = model(**cached_payload)
                    instance._initial_state = dict(instance._field_values)
                    instance._persisted = True
                    self.identity_map.add(instance)
                    return instance

            field = model._meta.get_field(field_name)
            column = field.column_name()
            quoted_column = self.dialect.quote_identifier(column)
            select_list = ", ".join(
                self.dialect.quote_identifier(f.column_name()) for f in model._meta.get_fields()
            )
            placeholder = self.dialect.parameter_placeholder()
            sql = (
                f"SELECT {select_list} FROM {self.dialect.format_table(model._meta.table_name)} "
                f"WHERE {quoted_column} = {placeholder} LIMIT 1"
            )
            cursor = self.execute(sql, (value,))
            row = cursor.fetchone()
            if not row:
                return None
            data = self._row_to_dict(cursor, row)
            return self._materialize(model, data)

    def refresh(self, instance: Model) -> Model:
        """Reload all scalar fields into an existing persisted instance."""

        with self._lock:
            pk_field = instance._meta.primary_key
            if not instance._persisted or instance in self.unit_of_work.deleted or pk_field is None:
                raise ValueError("Session.refresh requires a persisted model instance.")
            pk_name = pk_field.require_name()
            pk_value = getattr(instance, pk_name, None)
            if pk_value is None:
                raise ValueError("Session.refresh requires a non-null primary key.")

            select_list = ", ".join(
                self.dialect.quote_identifier(field.column_name())
                for field in instance._meta.get_fields()
            )
            table = self.dialect.format_table(instance._meta.table_name)
            pk_column = self.dialect.quote_identifier(pk_field.column_name())
            placeholder = self.dialect.parameter_placeholder()
            cursor = self.execute(
                f"SELECT {select_list} FROM {table} " f"WHERE {pk_column} = {placeholder} LIMIT 1",
                (pk_value,),
            )
            row = cursor.fetchone()
            if row is None:
                from ..query import DoesNotExist

                raise DoesNotExist(
                    f"{instance.__class__.__name__} with primary key {pk_value!r} does not exist."
                )

            data = self._row_to_dict(cursor, row)
            refreshed_values = {
                field.require_name(): field.to_python(data[field.column_name()])
                for field in instance._meta.get_fields()
            }
            instance._field_values = refreshed_values
            instance._initial_state = dict(refreshed_values)
            instance._related_cache.clear()
            instance._persisted = True
            self.unit_of_work.dirty.discard(instance)
            self.identity_map.add(instance)
            self._cache_instance(instance)
            return instance

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> Cursor:
        with self._lock:
            param_list = list(params or [])
            redacted = self._redact(param_list)

            def _record(elapsed_ms: float) -> None:
                self.performance.record(sql, redacted, elapsed_ms)

            with time_call(
                "session.execute",
                self.logger,
                sql=sql,
                params=redacted,
                threshold_ms=self.slow_query_ms,
                on_complete=_record,
            ):
                return self.adapter.execute(sql, param_list)

    def query(self, model: Type[Model]):
        """
        Return a QuerySet bound to this session for execution.
        """

        from ..query import QuerySet

        return QuerySet(model, dialect=self.dialect, session=self)

    # Many-to-many helpers --------------------------------------------- #
    def add_m2m(self, instance: Model, field_name: str, *related: Model) -> None:
        field = self._get_m2m_field(instance, field_name)
        manager = getattr(instance, field_name)
        manager.add(*related)
        self._invalidate_m2m_cache(instance, field, related)

    def remove_m2m(self, instance: Model, field_name: str, *related: Model) -> None:
        field = self._get_m2m_field(instance, field_name)
        manager = getattr(instance, field_name)
        manager.remove(*related)
        self._invalidate_m2m_cache(instance, field, related)

    def clear_m2m(self, instance: Model, field_name: str) -> None:
        field = self._get_m2m_field(instance, field_name)
        manager = getattr(instance, field_name)
        manager.clear()
        self._invalidate_m2m_cache(instance, field, [])

    def _materialize(self, model: Type[Model], data: dict[str, Any]) -> Model:
        pk_field = model._meta.primary_key
        pk_name = pk_field.require_name() if pk_field else None
        pk_value = data.get(pk_name) if pk_name else None
        if pk_name and pk_value is not None:
            cached = self.identity_map.get(model, pk_value)
            if cached:
                return cached
        instance = model(**data)
        if pk_name and pk_value is not None and getattr(instance, pk_name, None) is None:
            setattr(instance, pk_name, pk_value)
        instance._initial_state = dict(instance._field_values)
        instance._persisted = True
        self.identity_map.add(instance)
        self._cache_instance(instance)
        return instance

    def query_stats(self) -> list[dict[str, object]]:
        """
        Return collected performance statistics for the current session.
        """

        with self._lock:
            return self.performance.summary()

    def export_query_stats(
        self, *, reset: bool = False, include_samples: bool = False
    ) -> list[dict[str, object]]:
        with self._lock:
            stats = self.performance.export(include_samples=include_samples)
            if reset:
                self.performance.reset()
            return stats

    def reset_query_stats(self) -> None:
        with self._lock:
            self.performance.reset()

    def _clear_cached_state(self) -> None:
        with self._lock:
            self.identity_map.clear()
            self.cache.clear()

    # ------------------------------------------------------------------ #
    @contextmanager
    def transaction(self):
        """
        Provide nested transaction context with savepoint support.
        """

        self.begin()
        try:
            yield self
        except Exception:
            self.rollback()
            raise
        else:
            self.commit()

    # ------------------------------------------------------------------ #
    def _snapshot_uow(self) -> None:
        identity_instances = set(self.identity_map.values())
        participants = (
            identity_instances
            | set(self.unit_of_work.new)
            | set(self.unit_of_work.dirty)
            | set(self.unit_of_work.deleted)
        )
        snapshot = _SessionSnapshot(
            new=set(self.unit_of_work.new),
            dirty=set(self.unit_of_work.dirty),
            deleted=set(self.unit_of_work.deleted),
            model_states={instance: self._model_state(instance) for instance in participants},
            identity_instances=identity_instances,
        )
        self._uow_snapshots.append(snapshot)

    def _discard_uow_snapshot(self) -> None:
        if self._uow_snapshots:
            self._uow_snapshots.pop()

    def _restore_uow_snapshot(self) -> None:
        if not self._uow_snapshots:
            self.unit_of_work.clear()
            return
        snapshot = self._uow_snapshots.pop()
        for instance, state in snapshot.model_states.items():
            instance._field_values = dict(state.field_values)
            instance._initial_state = dict(state.initial_state)
            instance._related_cache = dict(state.related_cache)
            instance._persisted = state.persisted
        self.unit_of_work.new = set(snapshot.new)
        self.unit_of_work.dirty = set(snapshot.dirty)
        self.unit_of_work.deleted = set(snapshot.deleted)
        self.identity_map.clear()
        self.cache.clear()
        for instance in snapshot.identity_instances:
            self.identity_map.add(instance)
            if instance._persisted:
                self._cache_instance(instance)

    @staticmethod
    def _model_state(instance: Model) -> _ModelState:
        return _ModelState(
            field_values=dict(instance._field_values),
            initial_state=dict(instance._initial_state),
            related_cache=dict(instance._related_cache),
            persisted=instance._persisted,
        )

    def _capture_transaction_participant(self, instance: Model) -> None:
        for snapshot in self._uow_snapshots:
            if instance not in snapshot.model_states:
                snapshot.model_states[instance] = self._model_state(instance)

    # ------------------------------------------------------------------ #
    # Persistence helpers
    # ------------------------------------------------------------------ #
    def _persist_new(self, instance: Model) -> None:
        self._apply_managed_timestamps(instance, created=True)
        self.hooks.fire("before_validate", instance, session=self)
        instance.full_clean()
        self.hooks.fire("after_validate", instance, session=self)
        self.hooks.fire("before_save", instance, session=self, created=True)
        table = self.dialect.format_table(instance._meta.table_name)
        columns = []
        params = []
        for field in instance._meta.get_fields():
            field_name = field.require_name()
            if field.primary_key and getattr(instance, field_name, None) is None:
                continue
            raw_value = getattr(instance, field_name, None)
            value = self._normalize_db_value(field, raw_value)
            columns.append(self.dialect.quote_identifier(field.column_name()))
            params.append(value)

        placeholders = ", ".join(self.dialect.parameter_placeholder() for _ in columns)
        columns_sql = ", ".join(columns)
        sql = f"INSERT INTO {table} ({columns_sql}) VALUES ({placeholders})"
        cursor = self.execute(sql, params)

        pk_field = instance._meta.primary_key
        if pk_field and getattr(instance, pk_field.require_name(), None) is None:
            pk_name = pk_field.require_name()
            pk_value = self.adapter.last_insert_id(cursor, instance._meta.table_name, pk_name)
            setattr(instance, pk_name, pk_value)

        instance._initial_state = dict(instance._field_values)
        instance._persisted = True
        self.identity_map.add(instance)
        self.hooks.fire("after_save", instance, session=self, created=True)
        self._cache_instance(instance)

    def _persist_dirty(self, instance: Model) -> None:
        self._apply_managed_timestamps(instance, created=False)
        self.hooks.fire("before_validate", instance, session=self)
        instance.full_clean()
        self.hooks.fire("after_validate", instance, session=self)
        self.hooks.fire("before_save", instance, session=self, created=False)
        pk_field = instance._meta.primary_key
        if pk_field is None:
            raise ValueError(f"Model '{instance.__class__.__name__}' lacks a primary key.")
        pk_name = pk_field.require_name()
        pk_value = getattr(instance, pk_name)
        if pk_value is None:
            raise ValueError("Dirty instance missing primary key value.")

        set_clauses = []
        params = []
        for field in instance._meta.get_fields():
            if field.primary_key:
                continue
            field_name = field.require_name()
            raw_value = getattr(instance, field_name)
            value = self._normalize_db_value(field, raw_value)
            initial_value = instance._initial_state.get(field_name)
            if value != initial_value:
                set_clauses.append(
                    f"{self.dialect.quote_identifier(field.column_name())} = {self.dialect.parameter_placeholder()}"
                )
                params.append(value)

        if not set_clauses:
            return

        table = self.dialect.format_table(instance._meta.table_name)
        set_sql = ", ".join(set_clauses)
        pk_clause = f"{self.dialect.quote_identifier(pk_field.column_name())} = {self.dialect.parameter_placeholder()}"
        params.append(pk_value)
        sql = f"UPDATE {table} SET {set_sql} WHERE {pk_clause}"
        self.execute(sql, params)
        instance._initial_state = dict(instance._field_values)
        self.hooks.fire("after_save", instance, session=self, created=False)
        self._cache_instance(instance)

    def _persist_deleted(self, instance: Model) -> None:
        pk_field = instance._meta.primary_key
        if pk_field is None:
            raise ValueError(f"Model '{instance.__class__.__name__}' lacks a primary key.")
        pk_value = getattr(instance, pk_field.require_name())
        if pk_value is None:
            return
        self.hooks.fire("before_delete", instance, session=self)
        table = self.dialect.format_table(instance._meta.table_name)
        pk_clause = f"{self.dialect.quote_identifier(pk_field.column_name())} = {self.dialect.parameter_placeholder()}"
        sql = f"DELETE FROM {table} WHERE {pk_clause}"
        self.execute(sql, (pk_value,))
        self.identity_map.remove(instance)
        self.hooks.fire("after_delete", instance, session=self)
        self._invalidate_cache(instance)
        instance._persisted = False

    @staticmethod
    def _redact(params: Iterable[Any]) -> list[Any]:
        return redact_params(params)

    def _cache_instance(self, instance: Model) -> None:
        pk_field = instance._meta.primary_key
        if pk_field is None:
            return
        pk_value = getattr(instance, pk_field.require_name(), None)
        if pk_value is None:
            return
        self.cache.set(instance.__class__, pk_value, instance.to_dict())

    def _invalidate_cache(self, instance: Model) -> None:
        pk_field = instance._meta.primary_key
        if pk_field is None:
            return
        pk_value = getattr(instance, pk_field.require_name(), None)
        if pk_value is None:
            return
        self.cache.delete(instance.__class__, pk_value)

    def _invalidate_m2m_cache(
        self, instance: Model, field: ManyToManyField, related: Iterable[Model]
    ) -> None:
        related_list = list(related)
        field_name = field.require_name()
        if related_list:
            instance._related_cache.pop(field_name, None)
        else:
            instance._related_cache[field_name] = []
        related_name = field.related_name or f"{instance.__class__.__name__.lower()}_set"
        for rel in related_list:
            if hasattr(rel, "_related_cache"):
                rel._related_cache.pop(related_name, None)

    def _get_m2m_field(self, instance: Model, field_name: str) -> ManyToManyField:
        # Check declared many-to-many fields
        for field in instance._meta.many_to_many:
            if field.name == field_name:
                return field
        # Check reverse accessors via related_name
        from ..core.relations import ManyToManyField as M2MField

        for candidate, field in relation_registry.m2m_reverse.get(instance.__class__, []):
            name = field.related_name or f"{candidate.__name__.lower()}_set"
            if name == field_name and isinstance(field, M2MField):
                return field
        raise KeyError(
            f"Unknown many-to-many field '{field_name}' on model '{instance.__class__.__name__}'"
        )

    def _ensure_adapter_connected(self) -> None:
        state = getattr(self.adapter, "_state", True)
        if not state:
            self.adapter.connect(self.connection_config)

    @staticmethod
    def _row_to_dict(cursor: Cursor, row: Any) -> dict[str, Any]:
        if hasattr(row, "keys"):
            return dict(row)
        if hasattr(cursor, "description"):
            columns = [col[0] for col in cursor.description]
            return {col: row[idx] for idx, col in enumerate(columns)}
        raise ValueError("Unable to map database row to dictionary.")

    @staticmethod
    def current() -> "Session | None":
        """
        Return the current session bound in the execution context, if any.
        """

        return _current_session.get()

    @staticmethod
    def _normalize_db_value(field, value: Any) -> Any:
        from ..core.fields import DateTimeField
        from ..core.relations import RelatedField

        if isinstance(field, DateTimeField) and isinstance(value, datetime):
            return value.isoformat()
        if isinstance(field, RelatedField) and value is not None:
            if hasattr(value, "pk"):
                return value.pk
        return value

    @staticmethod
    def _apply_managed_timestamps(instance: Model, *, created: bool) -> None:
        from ..core.fields import DateTimeField

        timestamp = _utc_now()
        if not created:
            existing_values = [
                getattr(instance, field.require_name(), None)
                for field in instance._meta.get_fields()
                if isinstance(field, DateTimeField) and field.auto_now
            ]
            comparable = [
                (
                    value.astimezone(timezone.utc)
                    if value.tzinfo is not None
                    else value.replace(tzinfo=timezone.utc)
                )
                for value in existing_values
                if isinstance(value, datetime)
            ]
            if comparable:
                latest = max(comparable)
                if timestamp <= latest:
                    timestamp = latest + timedelta(microseconds=1)
        for field in instance._meta.get_fields():
            if not isinstance(field, DateTimeField):
                continue
            if field.auto_now or (created and field.auto_now_add):
                setattr(instance, field.require_name(), timestamp)
