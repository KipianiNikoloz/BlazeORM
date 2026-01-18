# Known Gaps (Actionable)
- Typing laxity: `pyproject.toml` is non-strict with `ignore_missing_imports=true`; warning flags are enabled, but further tightening (stricter config and type coverage) remains.
- Security redaction only masks obvious tokens in params; DSN redaction ignores sensitive query params. Improve redaction coverage and tests.
- Integration tests for Postgres/MySQL are env/driver-gated; no containerized/CI-backed runs to guarantee cross-dialect coverage.
- Thread-safety not guaranteed for Session/IdentityMap/Cache; no tests for concurrent use.
- Instructions folder is gitignored in `.gitignore`; new instruction files may be untracked unless explicitly added.
