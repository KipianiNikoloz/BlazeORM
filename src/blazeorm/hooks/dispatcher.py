"""
Hook dispatcher coordinating lifecycle events.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

from ..core.model import Model


HookHandler = Callable[..., None]


@dataclass(frozen=True)
class HookEvent:
    name: str


class HookDispatcher:
    """
    Maintains global and per-model hook handlers.
    """

    def __init__(self) -> None:
        self._global_handlers: Dict[str, List[HookHandler]] = defaultdict(list)
        self._model_handlers: Dict[Type[Model], Dict[str, List[HookHandler]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def register(self, event: str, handler: HookHandler, *, model: Optional[Type[Model]] = None) -> None:
        if model:
            self._model_handlers[model][event].append(handler)
        else:
            self._global_handlers[event].append(handler)

    def fire(self, event: str, instance: Optional[Model], **context: Any) -> None:
        handlers = list(self._global_handlers.get(event, []))
        model = instance.__class__ if instance is not None else None
        if model:
            handlers.extend(self._model_handlers.get(model, {}).get(event, []))
        for handler in handlers:
            handler(instance, **context)

    def clear(self) -> None:
        self._global_handlers.clear()
        self._model_handlers.clear()


hooks = HookDispatcher()
