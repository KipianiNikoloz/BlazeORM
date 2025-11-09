"""
Lifecycle hooks registry for BlazeORM models.
"""

from .dispatcher import HookDispatcher, HookEvent, hooks

__all__ = ["HookDispatcher", "HookEvent", "hooks"]
