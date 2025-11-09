"""
BlazeORM public package initialization.

This module exposes the primary public APIs while deferring heavy imports
to maintain quick startup time.
"""

from .core.model import Model, ModelConfigurationError  # noqa: F401
from .core.fields import (
    AutoField,
    BooleanField,
    DateTimeField,
    FloatField,
    IntegerField,
    StringField,
)  # noqa: F401
from .hooks import hooks  # noqa: F401
from .persistence import Session  # noqa: F401
from .query import Q, QuerySet  # noqa: F401
from .schema import MigrationEngine, MigrationOperation, SchemaBuilder  # noqa: F401
from .validation import ValidationError  # noqa: F401

__all__ = [
    "Model",
    "AutoField",
    "BooleanField",
    "DateTimeField",
    "FloatField",
    "IntegerField",
    "StringField",
    "ModelConfigurationError",
    "Session",
    "QuerySet",
    "Q",
    "SchemaBuilder",
    "MigrationEngine",
    "MigrationOperation",
    "ValidationError",
    "hooks",
]
