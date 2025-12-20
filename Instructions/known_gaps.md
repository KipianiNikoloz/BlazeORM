# Known Gaps (Actionable)
- `Session.get` uses hard-coded `?` placeholders, failing on Postgres/MySQL (`src/blazeorm/persistence/session.py:143-170`); add dialect-aware handling + tests.
- Typing laxity: `pyproject.toml` is non-strict with `ignore_missing_imports=true`; tighten typing (flags/config) and address any remaining mypy issues.
- Schema builder does not emit FK/index constraints for relations (`src/blazeorm/schema/builder.py`); migrations rely on bare columns and unique constraints only.
- Security redaction only masks obvious tokens in params; DSN redaction ignores sensitive query params. Improve redaction coverage and tests.
- Integration tests for Postgres/MySQL are env/driver-gated; no containerized/CI-backed runs to guarantee cross-dialect coverage.
- Thread-safety not guaranteed for Session/IdentityMap/Cache; no tests for concurrent use.
- Instructions folder is gitignored in `.gitignore`; new instruction files may be untracked unless explicitly added.
