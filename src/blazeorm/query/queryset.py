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
    from ..persistence.session import Session


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
        select_related: Tuple[str, ...] = (),
        prefetch_related: Tuple[str, ...] = (),
        session: "Session | None" = None,
    ) -> None:
        self.model = model
        self.dialect = dialect or SQLiteDialect()
        self._where = where or Q()
        self._ordering = ordering
        self._limit = limit
        self._offset = offset
        self._select_related = select_related
        self._prefetch_related = prefetch_related
        self._session = session

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

    def select_related(self, *fields: str) -> "QuerySet":
        if not fields:
            raise ValueError("select_related() requires at least one relationship name.")
        combined = tuple(dict.fromkeys(self._select_related + fields))
        return self._clone(select_related=combined)

    def prefetch_related(self, *fields: str) -> "QuerySet":
        if not fields:
            raise ValueError("prefetch_related() requires at least one relationship name.")
        combined = tuple(dict.fromkeys(self._prefetch_related + fields))
        return self._clone(prefetch_related=combined)

    def to_sql(self) -> tuple[str, list[Any]]:
        compiler = SQLCompiler(
            model=self.model,
            dialect=self.dialect,
            where=self._where,
            ordering=self._ordering,
            limit=self._limit,
            offset=self._offset,
            select_related=self._select_related,
        )
        return compiler.compile()

    # Iteration placeholder (will integrate with persistence later)
    def __iter__(self) -> Iterable["Model"]:
        if self._session is None:
            raise RuntimeError("QuerySet iteration requires a bound Session. Use Session.query(model).")
        sql, params = self.to_sql()
        cursor = self._session.execute(sql, params)
        rows = cursor.fetchall()
        for row in rows:
            data = self._row_to_dict(cursor, row)
            yield self._session._materialize(self.model, data)

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
            "select_related": overrides.get("select_related", self._select_related),
            "prefetch_related": overrides.get("prefetch_related", self._prefetch_related),
            "session": overrides.get("session", self._session),
        }
        return QuerySet(**params)

    @staticmethod
    def _row_to_dict(cursor, row) -> dict[str, Any]:
        if hasattr(row, "keys"):
            return dict(row)
        if hasattr(cursor, "description"):
            columns = [col[0] for col in cursor.description]
            return {col: row[idx] for idx, col in enumerate(columns)}
        raise ValueError("Unable to map database row to dictionary.")


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

    def select_related(self, *fields: str) -> QuerySet:
        return self.all().select_related(*fields)

    def prefetch_related(self, *fields: str) -> QuerySet:
        return self.all().prefetch_related(*fields)
