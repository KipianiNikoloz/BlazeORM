"""
Validation error hierarchy for BlazeORM.
"""

from __future__ import annotations

from typing import Dict, List, Mapping


class ValidationError(Exception):
    """
    Aggregated validation error storing field-to-messages mapping.
    """

    def __init__(self, errors: Mapping[str, List[str]]) -> None:
        self.errors: Dict[str, List[str]] = {
            key: list(messages) for key, messages in errors.items()
        }
        message = self._format_message()
        super().__init__(message)

    def _format_message(self) -> str:
        segments = []
        for field, messages in self.errors.items():
            prefix = field if field != "__all__" else "non-field"
            combined = "; ".join(messages)
            segments.append(f"{prefix}: {combined}")
        return "; ".join(segments)
