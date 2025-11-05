"""
Naming utilities for BlazeORM.
"""

import re


_FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def camel_to_snake(name: str) -> str:
    """
    Convert ``CamelCase`` names to ``snake_case`` for table naming.
    """
    step1 = _FIRST_CAP_RE.sub(r"\1_\2", name)
    snake = _ALL_CAP_RE.sub(r"\1_\2", step1).lower()
    return snake
