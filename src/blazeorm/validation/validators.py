"""
Built-in validator helpers.
"""

from __future__ import annotations

import re
from typing import Any, Protocol


class Validator(Protocol):
    def __call__(self, value: Any) -> None: ...


class MinValueValidator:
    def __init__(self, minimum: float, message: str | None = None) -> None:
        self.minimum = minimum
        self.message = message or f"Ensure value is greater than or equal to {minimum}."

    def __call__(self, value: Any) -> None:
        if value is None:
            return
        if value < self.minimum:
            raise ValueError(self.message)


class MaxValueValidator:
    def __init__(self, maximum: float, message: str | None = None) -> None:
        self.maximum = maximum
        self.message = message or f"Ensure value is less than or equal to {maximum}."

    def __call__(self, value: Any) -> None:
        if value is None:
            return
        if value > self.maximum:
            raise ValueError(self.message)


class RegexValidator:
    def __init__(self, pattern: str, message: str | None = None) -> None:
        self.pattern = re.compile(pattern)
        self.message = message or "Value does not match required pattern."

    def __call__(self, value: Any) -> None:
        if value is None:
            return
        if not isinstance(value, str):
            raise ValueError("Value must be a string for RegexValidator.")
        if not self.pattern.match(value):
            raise ValueError(self.message)
