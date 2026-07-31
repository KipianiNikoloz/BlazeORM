# Changelog

All notable changes to this project will be documented here.

## [Unreleased]
- No changes yet.
- Replaced ad-hoc development virtual environments and pip-based CI/release setup with a locked `uv` workflow.
- Added efficient `values()` and `values_list()` field projections to QuerySet and QueryManager.
- Added portable numeric aggregate terminals with correct ordered-slice semantics.

## [0.3.0] - 2026-07-31
- Added functional `Model.save()` and `Model.delete()` methods with explicit or context-bound Session resolution.
- Added model lifecycle tracking for assigned-key inserts, loaded-instance updates, deletion, and autocommit parity.
- Corrected managed datetime fields so `auto_now` advances on writes and `auto_now_add` remains creation-only.
- Added `Session.refresh()` for cache-bypassing, in-place model reloads and ISO datetime hydration.
- Made the test suite fail on leaked database connections and ignored local coverage artifacts.

## [0.2.0] - 2026-07-31
- Added cloned scalar and relationship field inheritance from abstract models, including conflict and primary-key rules.
- Added `first`, `get`, `count`, and `exists` terminal operations to QuerySet and QueryManager.
- Added public `QueryError`, `DoesNotExist`, and `MultipleObjectsReturned` exceptions.
- Added portable `in`, `isnull`, prefix, suffix, and case-insensitive query lookups.
- Corrected `iexact` SQL so case-insensitive behavior is consistent across supported databases.

## [0.1.0] - 2025-12-06
- Initial packaging scaffolding (`pyproject.toml`, version export, extras) plus CI (ruff/black/isort/mypy/pytest).
- Adapter hardening for Postgres/MySQL (reconnect, autocommit respect) and env-driven integration smoke tests.
- Eager loading and many-to-many enhancements with expanded examples (blog, library).
- Documentation overhaul with module-level READMEs and updated Instructions.
