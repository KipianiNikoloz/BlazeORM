"""
Unit of Work implementation batching persistence operations.
"""

from __future__ import annotations

from typing import Iterable, Set

from ..core.model import Model


class UnitOfWork:
    """
    Tracks new, dirty, and deleted objects within a session.
    """

    def __init__(self) -> None:
        self.new: Set[Model] = set()
        self.dirty: Set[Model] = set()
        self.deleted: Set[Model] = set()

    # Registration methods ----------------------------------------------
    def register_new(self, instance: Model) -> None:
        self.new.add(instance)

    def register_dirty(self, instance: Model) -> None:
        if instance not in self.new:
            self.dirty.add(instance)

    def register_deleted(self, instance: Model) -> None:
        self.new.discard(instance)
        self.dirty.discard(instance)
        self.deleted.add(instance)

    def collect_dirty(self, candidates: Iterable[Model]) -> None:
        for instance in candidates:
            if instance not in self.new and instance.is_dirty():
                self.register_dirty(instance)

    def clear(self) -> None:
        self.new.clear()
        self.dirty.clear()
        self.deleted.clear()
