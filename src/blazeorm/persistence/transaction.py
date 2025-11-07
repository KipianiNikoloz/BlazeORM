"""
Transaction manager handling nested transactions and savepoints.
"""

from __future__ import annotations

import itertools
from contextlib import contextmanager
from typing import Generator, List

from ..adapters.base import DatabaseAdapter
from ..dialects.base import Dialect


class TransactionError(RuntimeError):
    pass


class TransactionManager:
    """
    Coordinates begin/commit/rollback with optional savepoint support.
    """

    def __init__(self, adapter: DatabaseAdapter, dialect: Dialect) -> None:
        self.adapter = adapter
        self.dialect = dialect
        self._stack: List[str | None] = []
        self._savepoint_counter = itertools.count(1)

    @property
    def depth(self) -> int:
        return len(self._stack)

    def begin(self) -> None:
        if self.depth == 0:
            self.adapter.begin()
            self._stack.append(None)
            return

        if not self.dialect.capabilities.supports_savepoints:
            raise TransactionError("Nested transactions not supported by current dialect.")

        name = self._next_savepoint_name()
        self.adapter.execute(f"SAVEPOINT {name}")
        self._stack.append(name)

    def commit(self) -> None:
        if self.depth == 0:
            raise TransactionError("No active transaction to commit.")

        savepoint_name = self._stack.pop()
        if savepoint_name is None:
            self.adapter.commit()
            return

        self.adapter.execute(f"RELEASE SAVEPOINT {savepoint_name}")

    def rollback(self) -> None:
        if self.depth == 0:
            raise TransactionError("No active transaction to roll back.")

        savepoint_name = self._stack.pop()
        if savepoint_name is None:
            self.adapter.rollback()
            return

        self.adapter.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
        self.adapter.execute(f"RELEASE SAVEPOINT {savepoint_name}")

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        self.begin()
        try:
            yield
        except Exception:
            self.rollback()
            raise
        else:
            self.commit()

    def _next_savepoint_name(self) -> str:
        return f"sp_{next(self._savepoint_counter)}"
