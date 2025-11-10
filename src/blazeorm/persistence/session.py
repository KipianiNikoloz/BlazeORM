"""
Session management coordinating adapters, unit of work, and identity map.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterable, Optional, Type

from ..adapters.base import ConnectionConfig, DatabaseAdapter
from ..core.model import Model
from ..dialects.base import Dialect
from ..dialects.sqlite import SQLiteDialect
from ..utils import get_logger, time_call
from ..cache import CacheBackend, NoOpCache
from .identity_map import IdentityMap
from .transaction import TransactionManager
from .unit_of_work import UnitOfWork


if TYPE_CHECKING:
    from ..hooks import HookDispatcher


class Session:
    """
    Coordinates persistence operations for a set of model instances.
    """

    def __init__(
        self,
        adapter: DatabaseAdapter,
        *,
        connection_config: Optional[ConnectionConfig] = None,
        autocommit: bool = False,
        cache_backend: Optional[CacheBackend] = None,
    ) -> None:
        self.adapter = adapter
        self.autocommit = autocommit
        self.dialect: Dialect = adapter.dialect if hasattr(adapter, "dialect") else SQLiteDialect()
        self.connection_config = connection_config or ConnectionConfig(url="sqlite:///:memory:")
        self.identity_map = IdentityMap()
        self.unit_of_work = UnitOfWork()
        self.transaction_manager = TransactionManager(adapter, self.dialect)
        self._uow_snapshots: list[tuple[set[Model], set[Model], set[Model]]] = []
        self.cache = cache_backend or NoOpCache()
        from ..hooks import hooks

        self.hooks = hooks
        self.logger = get_logger("persistence.session")
        self.adapter.connect(self.connection_config)

    # ------------------------------------------------------------------ #
    # Context management
    # ------------------------------------------------------------------ #
    def __enter__(self) -> "Session":
        self.begin()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            self.close()

    # ------------------------------------------------------------------ #
    def begin(self) -> None:
        self.transaction_manager.begin()
        self._snapshot_uow()

    def commit(self) -> None:
        if self.transaction_manager.depth == 0:
            self.begin()
        self.flush()
        self.transaction_manager.commit()
        self._discard_uow_snapshot()
        if self.transaction_manager.depth == 0:
            self.unit_of_work.clear()
            self.hooks.fire("after_commit", None, session=self)

    def rollback(self) -> None:
        self.transaction_manager.rollback()
        self._restore_uow_snapshot()

    def close(self) -> None:
        self.adapter.close()
        self.identity_map.clear()
        self._uow_snapshots.clear()

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    def add(self, instance: Model) -> None:
        self.unit_of_work.register_new(instance)
        if self.autocommit:
            self.commit()

    def delete(self, instance: Model) -> None:
        self.unit_of_work.register_deleted(instance)
        if self.autocommit:
            self.commit()

    def mark_dirty(self, instance: Model) -> None:
        self.unit_of_work.register_dirty(instance)

    # ------------------------------------------------------------------ #
    def flush(self) -> None:
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
        if len(filters) != 1:
            raise ValueError("Session.get currently supports exactly one filter.")
        field_name, value = next(iter(filters.items()))

        if field_name == model._meta.primary_key.name:
            cached = self.identity_map.get(model, value)
            if cached is not None:
                return cached
            cached_payload = self.cache.get(model, value)
            if cached_payload is not None:
                instance = model(**cached_payload)
                instance._initial_state = dict(instance._field_values)
                self.identity_map.add(instance)
                return instance

        column = model._meta.get_field(field_name).db_column or field_name
        quoted_column = self.dialect.quote_identifier(column)
        select_list = ", ".join(
            self.dialect.quote_identifier(f.db_column or f.name) for f in model._meta.get_fields()
        )
        sql = f"SELECT {select_list} FROM {self.dialect.format_table(model._meta.table_name)} WHERE {quoted_column} = ? LIMIT 1"
        cursor = self.execute(sql, (value,))
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        instance = model(**data)
        # Ensure primary key attribute is set if not in data (should be)
        if model._meta.primary_key and model._meta.primary_key.name not in data:
            setattr(instance, model._meta.primary_key.name, row[model._meta.primary_key.name])
        instance._initial_state = dict(instance._field_values)
        self.identity_map.add(instance)
        self._cache_instance(instance)
        return instance

    def execute(self, sql: str, params: Iterable[Any] | None = None):
        param_list = list(params or [])
        with time_call("session.execute", self.logger, sql=sql, params=self._redact(param_list), threshold_ms=200):
            return self.adapter.execute(sql, param_list)

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
        snapshot = (
            set(self.unit_of_work.new),
            set(self.unit_of_work.dirty),
            set(self.unit_of_work.deleted),
        )
        self._uow_snapshots.append(snapshot)

    def _discard_uow_snapshot(self) -> None:
        if self._uow_snapshots:
            self._uow_snapshots.pop()

    def _restore_uow_snapshot(self) -> None:
        if not self._uow_snapshots:
            self.unit_of_work.clear()
            return
        new_snapshot, dirty_snapshot, deleted_snapshot = self._uow_snapshots.pop()
        self.unit_of_work.new = set(new_snapshot)
        self.unit_of_work.dirty = set(dirty_snapshot)
        self.unit_of_work.deleted = set(deleted_snapshot)

    # ------------------------------------------------------------------ #
    # Persistence helpers
    # ------------------------------------------------------------------ #
    def _persist_new(self, instance: Model) -> None:
        self.hooks.fire("before_validate", instance, session=self)
        instance.full_clean()
        self.hooks.fire("after_validate", instance, session=self)
        self.hooks.fire("before_save", instance, session=self, created=True)
        table = self.dialect.format_table(instance._meta.table_name)
        columns = []
        params = []
        for field in instance._meta.get_fields():
            if field.primary_key and getattr(instance, field.name, None) is None:
                continue
            value = getattr(instance, field.name, None)
            columns.append(self.dialect.quote_identifier(field.db_column or field.name))
            params.append(value)

        placeholders = ", ".join(self.dialect.parameter_placeholder() for _ in columns)
        columns_sql = ", ".join(columns)
        sql = f"INSERT INTO {table} ({columns_sql}) VALUES ({placeholders})"
        cursor = self.execute(sql, params)

        pk_field = instance._meta.primary_key
        if pk_field and getattr(instance, pk_field.name, None) is None:
            pk_value = self.adapter.last_insert_id(cursor, instance._meta.table_name, pk_field.name)
            setattr(instance, pk_field.name, pk_value)

        instance._initial_state = dict(instance._field_values)
        self.identity_map.add(instance)
        self.hooks.fire("after_save", instance, session=self, created=True)
        self._cache_instance(instance)

    def _persist_dirty(self, instance: Model) -> None:
        self.hooks.fire("before_validate", instance, session=self)
        instance.full_clean()
        self.hooks.fire("after_validate", instance, session=self)
        self.hooks.fire("before_save", instance, session=self, created=False)
        pk_field = instance._meta.primary_key
        if pk_field is None:
            raise ValueError(f"Model '{instance.__class__.__name__}' lacks a primary key.")
        pk_value = getattr(instance, pk_field.name)
        if pk_value is None:
            raise ValueError("Dirty instance missing primary key value.")

        set_clauses = []
        params = []
        for field in instance._meta.get_fields():
            if field.primary_key:
                continue
            value = getattr(instance, field.name)
            initial_value = instance._initial_state.get(field.name)
            if value != initial_value:
                set_clauses.append(
                    f"{self.dialect.quote_identifier(field.db_column or field.name)} = {self.dialect.parameter_placeholder()}"
                )
                params.append(value)

        if not set_clauses:
            return

        table = self.dialect.format_table(instance._meta.table_name)
        set_sql = ", ".join(set_clauses)
        pk_clause = f"{self.dialect.quote_identifier(pk_field.db_column or pk_field.name)} = {self.dialect.parameter_placeholder()}"
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
        pk_value = getattr(instance, pk_field.name)
        if pk_value is None:
            return
        self.hooks.fire("before_delete", instance, session=self)
        table = self.dialect.format_table(instance._meta.table_name)
        pk_clause = f"{self.dialect.quote_identifier(pk_field.db_column or pk_field.name)} = {self.dialect.parameter_placeholder()}"
        sql = f"DELETE FROM {table} WHERE {pk_clause}"
        self.execute(sql, (pk_value,))
        self.identity_map.remove(instance)
        self.hooks.fire("after_delete", instance, session=self)
        self._invalidate_cache(instance)

    @staticmethod
    def _redact(params: Iterable[Any]) -> list[Any]:
        redacted = []
        for value in params:
            if isinstance(value, str) and any(token in value.lower() for token in ("password", "secret", "token")):
                redacted.append("***")
            else:
                redacted.append(value)
        return redacted

    def _cache_instance(self, instance: Model) -> None:
        pk_field = instance._meta.primary_key
        if pk_field is None:
            return
        pk_value = getattr(instance, pk_field.name, None)
        if pk_value is None:
            return
        self.cache.set(instance.__class__, pk_value, instance.to_dict())

    def _invalidate_cache(self, instance: Model) -> None:
        pk_field = instance._meta.primary_key
        if pk_field is None:
            return
        pk_value = getattr(instance, pk_field.name, None)
        if pk_value is None:
            return
        self.cache.delete(instance.__class__, pk_value)
