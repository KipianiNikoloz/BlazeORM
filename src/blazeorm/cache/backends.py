"""Cache backend implementations."""

from __future__ import annotations

from threading import RLock
from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol, Tuple, Type

if TYPE_CHECKING:
    from ..core.model import Model


class CacheBackend(Protocol):
    def get(self, model: Type["Model"], pk: Any) -> Optional[Dict[str, Any]]: ...

    def set(self, model: Type["Model"], pk: Any, data: Dict[str, Any]) -> None: ...

    def delete(self, model: Type["Model"], pk: Any) -> None: ...

    def clear(self) -> None: ...


class NoOpCache:
    def __init__(self) -> None:
        self._lock = RLock()

    def get(self, model: Type["Model"], pk: Any) -> Optional[Dict[str, Any]]:
        with self._lock:
            return None

    def set(self, model: Type["Model"], pk: Any, data: Dict[str, Any]) -> None:
        with self._lock:
            return None

    def delete(self, model: Type["Model"], pk: Any) -> None:
        with self._lock:
            return None

    def clear(self) -> None:
        with self._lock:
            return None


class InMemoryCache:
    def __init__(self) -> None:
        self._store: Dict[Tuple[Type["Model"], Any], Dict[str, Any]] = {}
        self._lock = RLock()

    def get(self, model: Type["Model"], pk: Any) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._store.get((model, pk))

    def set(self, model: Type["Model"], pk: Any, data: Dict[str, Any]) -> None:
        with self._lock:
            self._store[(model, pk)] = dict(data)

    def delete(self, model: Type["Model"], pk: Any) -> None:
        with self._lock:
            self._store.pop((model, pk), None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
