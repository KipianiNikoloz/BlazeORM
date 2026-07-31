# Changelog

All notable changes to this project will be documented here.

## [Unreleased]
- Added portable `in`, `isnull`, prefix, suffix, and case-insensitive query lookups.
- Corrected `iexact` SQL so case-insensitive behavior is consistent across supported databases.

## [0.1.0] - 2025-12-06
- Initial packaging scaffolding (`pyproject.toml`, version export, extras) plus CI (ruff/black/isort/mypy/pytest).
- Adapter hardening for Postgres/MySQL (reconnect, autocommit respect) and env-driven integration smoke tests.
- Eager loading and many-to-many enhancements with expanded examples (blog, library).
- Documentation overhaul with module-level READMEs and updated Instructions.
