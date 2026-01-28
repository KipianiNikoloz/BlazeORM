"""
Identity map ensuring a single in-memory instance per row.
"""

from __future__ import annotations

from threading import RLock
from typing import Dict, Tuple, Type

from ..core.model import Model


class IdentityMap:
    """
    Stores model instances keyed by (model, primary key).
    """

    def __init__(self) -> None:
        self._store: Dict[Tuple[Type[Model], object], Model] = {}
        self._lock = RLock()

    @staticmethod
    def _make_key(instance_or_model, pk) -> Tuple[Type[Model], object]:
        if isinstance(instance_or_model, type):
            model = instance_or_model
        else:
            model = instance_or_model.__class__
        return (model, pk)

    def add(self, instance: Model) -> None:
        pk = instance.pk
        if pk is None:
            return
        key = self._make_key(instance, pk)
        with self._lock:
            self._store[key] = instance

    def get(self, model: Type[Model], pk) -> Model | None:
        key = self._make_key(model, pk)
        with self._lock:
            return self._store.get(key)

    def remove(self, instance: Model) -> None:
        pk = instance.pk
        if pk is None:
            return
        key = self._make_key(instance, pk)
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def values(self):
        with self._lock:
            return list(self._store.values())

    def __contains__(self, instance: Model) -> bool:
        pk = instance.pk
        if pk is None:
            return False
        key = self._make_key(instance, pk)
        with self._lock:
            return key in self._store
