Security Utilities
==================

What Lives Here
---------------
- `dsns.py`: DSN parsing/redaction, `ConnectionConfig.from_env/from_dsn`, descriptive labels, and credential hiding.
- `destructive.py`: Helpers for confirming destructive operations (used by migrations/schema).

Key Behaviors
-------------
- DSN utilities:
  - Parse DSNs into `ConnectionConfig` with options (autocommit, isolation level, timeouts).
  - Redact credentials in logs; expose `redacted_dsn()`.
  - Validate environment-driven configuration via `from_env`.
- Destructive operations:
  - Emit warnings/confirmation prompts for drops or migration steps marked destructive.

Testing References
------------------
- `tests/security/test_security.py`.

