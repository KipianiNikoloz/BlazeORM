"""
Database adapter interfaces and implementations.
"""

from .base import (
    AdapterConfigurationError,
    AdapterConnectionError,
    AdapterError,
    AdapterExecutionError,
    AdapterTransactionError,
    ConnectionConfig,
    DatabaseAdapter,
    SSLConfig,
)
from .mysql import MySQLAdapter
from .postgres import PostgresAdapter
from .sqlite import SQLiteAdapter

__all__ = [
    "ConnectionConfig",
    "DatabaseAdapter",
    "SSLConfig",
    "AdapterError",
    "AdapterConfigurationError",
    "AdapterConnectionError",
    "AdapterExecutionError",
    "AdapterTransactionError",
    "SQLiteAdapter",
    "PostgresAdapter",
    "MySQLAdapter",
]
