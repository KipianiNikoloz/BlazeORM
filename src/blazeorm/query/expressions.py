"""
Expression tree primitives for query construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Tuple


AND = "AND"
OR = "OR"


def _normalize_items(items: Iterable[Tuple[str, Any]]) -> List[Tuple[str, Any]]:
    return list(items)


@dataclass
class Q:
    """
    Boolean expression container similar to Django-style Q objects.
    """

    children: List[Any] = field(default_factory=list)
    connector: str = AND
    negated: bool = False

    def __init__(self, *children: Any, **lookups: Any) -> None:
        self.children = []
        if children:
            self.children.extend(children)
        if lookups:
            self.children.extend(_normalize_items(lookups.items()))
        self.connector = AND
        self.negated = False

    def __or__(self, other: "Q") -> "Q":
        return self._combine(other, OR)

    def __and__(self, other: "Q") -> "Q":
        return self._combine(other, AND)

    def __invert__(self) -> "Q":
        q = self._clone()
        q.negated = not q.negated
        return q

    # Internal helpers -------------------------------------------------
    def _clone(self) -> "Q":
        clone = Q()
        clone.children = list(self.children)
        clone.connector = self.connector
        clone.negated = self.negated
        return clone

    def _combine(self, other: "Q", connector: str) -> "Q":
        q = Q()
        q.children = [self._clone(), other._clone()]
        q.connector = connector
        return q

    def add(self, node: Any, connector: str) -> None:
        if self.children:
            self.children.append(connector)
        self.children.append(node)

    def is_empty(self) -> bool:
        return not self.children
