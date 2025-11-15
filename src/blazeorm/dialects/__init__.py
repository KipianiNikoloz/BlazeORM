"""
Dialect strategy registry.
"""

from .base import Dialect, DialectCapabilities
from .postgres import PostgresDialect
from .sqlite import SQLiteDialect

__all__ = ["Dialect", "DialectCapabilities", "SQLiteDialect", "PostgresDialect"]
