Security Utilities
==================

What Lives Here
---------------
- `dsns.py`: DSN parsing/redaction, `ConnectionConfig.from_env/from_dsn`, descriptive labels, and credential hiding.
- `redaction.py`: Shared redaction helpers for DSN query params and logged parameters.
- `destructive.py`: Helpers for confirming destructive operations (used by migrations/schema).

Key Behaviors
-------------
- DSN utilities:
  - Parse DSNs into `ConnectionConfig` with options (autocommit, isolation level, timeouts).
  - Redact credentials and sensitive query params in logs; expose `redacted_dsn()`.
  - Validate environment-driven configuration via `from_env`.
  - Redact sensitive parameter values in adapter/session logs.
- Destructive operations:
  - Emit warnings/confirmation prompts for drops or migration steps marked destructive.

Testing References
------------------
- `tests/security/test_security.py`.
