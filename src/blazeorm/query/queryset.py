"""
QuerySet implementation providing a chainable query API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Optional, Tuple
from ..dialects.sqlite import SQLiteDialect
from .compiler import SQLCompiler
from .expressions import Q


if TYPE_CHECKING:
    from ..core.model import Model


class QuerySet:
    """
    Lightweight QuerySet capable of compiling to SQL strings.
    Execution will be delegated to persistence layer in later milestones.
    """

    def __init__(
        self,
        model: type["Model"],
        *,
        dialect=None,
        where: Optional[Q] = None,
        ordering: Tuple[str, ...] = (),
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> None:
        self.model = model
        self.dialect = dialect or SQLiteDialect()
        self._where = where or Q()
        self._ordering = ordering
        self._limit = limit
        self._offset = offset

    # Public API --------------------------------------------------------
    def filter(self, **lookups: Any) -> "QuerySet":
        return self._clone(where=self._add_q(Q(**lookups)))

    def exclude(self, **lookups: Any) -> "QuerySet":
        return self._clone(where=self._add_q(~Q(**lookups)))

    def where(self, q_object: Q) -> "QuerySet":
        return self._clone(where=self._add_q(q_object))

    def order_by(self, *fields: str) -> "QuerySet":
        return self._clone(ordering=tuple(fields))

    def limit(self, value: int) -> "QuerySet":
        return self._clone(limit=value)

    def offset(self, value: int) -> "QuerySet":
        return self._clone(offset=value)

    def to_sql(self) -> tuple[str, list[Any]]:
        compiler = SQLCompiler(
            model=self.model,
            dialect=self.dialect,
            where=self._where,
            ordering=self._ordering,
            limit=self._limit,
            offset=self._offset,
        )
        return compiler.compile()

    # Iteration placeholder (will integrate with persistence later)
    def __iter__(self) -> Iterable["Model"]:
        raise NotImplementedError("QuerySet iteration will be provided by persistence layer.")

    # Internal helpers --------------------------------------------------
    def _add_q(self, q_object: Q) -> Q:
        if self._where.is_empty():
            return q_object
        return self._where & q_object

    def _clone(self, **overrides: Any) -> "QuerySet":
        params = {
            "model": self.model,
            "dialect": self.dialect,
            "where": overrides.get("where", self._where),
            "ordering": overrides.get("ordering", self._ordering),
            "limit": overrides.get("limit", self._limit),
            "offset": overrides.get("offset", self._offset),
        }
        return QuerySet(**params)


class QueryManager:
    """
    Default manager for models providing QuerySet access.
    """

    def __init__(self, model: type["Model"]) -> None:
        self.model = model

    def all(self) -> QuerySet:
        return QuerySet(self.model)

    def filter(self, **lookups: Any) -> QuerySet:
        return self.all().filter(**lookups)

    def exclude(self, **lookups: Any) -> QuerySet:
        return self.all().exclude(**lookups)

    def where(self, q_object: Q) -> QuerySet:
        return self.all().where(q_object)
