"""Declarative model-level constraints and indexes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class UniqueConstraint:
    fields: Sequence[str]
    name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", _validate_fields(self.fields))
        _validate_name(self.name)


@dataclass(frozen=True)
class Index:
    fields: Sequence[str]
    name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", _validate_fields(self.fields))
        _validate_name(self.name)


def _validate_fields(fields: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(fields)
    if not normalized:
        raise ValueError("Constraint/index metadata requires at least one field.")
    if any(not isinstance(name, str) or not name for name in normalized):
        raise ValueError("Constraint/index field names must be non-empty strings.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Constraint/index field names must be unique.")
    return normalized


def _validate_name(name: str | None) -> None:
    if name is not None and (not isinstance(name, str) or not name):
        raise ValueError("Constraint/index names must be non-empty strings.")
