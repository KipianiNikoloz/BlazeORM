Hooks
=====

What Lives Here
---------------
- `dispatcher.py`: Hook dispatcher that registers handlers per event and model.
- `__init__.py`: Exposes global dispatcher (`hooks`).

Key Behaviors
-------------
- Events: `before/after_validate`, `before/after_save`, `before/after_delete`, `after_commit`.
- Supports global handlers or model-specific handlers.
- Session triggers hooks around persistence operations.

Usage Notes
-----------
- Register handlers via `Model.register_hook(event, handler)` or directly on `hooks`.
- Handlers receive `instance` and `session` context.

Testing References
------------------
- `tests/hooks/test_hooks.py`.

