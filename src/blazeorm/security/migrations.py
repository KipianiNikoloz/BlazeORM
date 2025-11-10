"""Migration safety helpers."""

from __future__ import annotations

import logging

logger = logging.getLogger("blazeorm.migrations")


def confirm_destructive_operation(operation: str, *, force: bool = False) -> None:
    if force:
        return
    raise RuntimeError(
        f"Destructive migration operation '{operation}' requires explicit confirmation (pass force=True)."
    )
