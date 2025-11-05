"""
Dialect strategy registry.
"""

from .base import Dialect, DialectCapabilities
from .sqlite import SQLiteDialect

__all__ = ["Dialect", "DialectCapabilities", "SQLiteDialect"]
