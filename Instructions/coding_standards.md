# Coding Standards (For Agents)
Follow these rules exactly; they are written for LLMs and reviewers.

## Mandatory Behavior
- Do not change behavior silently; call out any breaking or user-visible change.
- Do not assume SQLite-only semantics; every change must consider Postgres/MySQL dialects and adapter validation.
- Do not bypass adapters/dialects (no raw driver connections or string interpolation that skips placeholder validation).
- Do not disable or weaken tests/mypy/linters to "make CI pass"; fix the code or document why a check is skipped.
- Add or adjust tests when changing behavior; prefer targeted pytest cases in the relevant domain folder.
- Update `current_state.md` (and `known_gaps.md`/`plan.md` if affected) after any meaningful change.
- Prefer explicit errors over silent fallbacks; validate inputs and raise clear exceptions.
- Maintain structured logging/redaction patterns already in adapters/session; use `time_call`, `PerformanceTracker`, and redaction helpers when relevant.

## Implementation Expectations
- Obey architecture invariants: session-bound execution, adapter-mediated SQL, dialect-aware placeholders, identity-map reuse, destructive migration confirmation.
- Keep code typed (PEP 484) and remove `# mypy: ignore-errors` where feasible; avoid introducing new broad ignores.
- Keep design small and reviewable; preserve backward compatibility unless explicitly directed.
- When touching relationships/eager loading, confirm both forward and reverse/m2m paths plus cache invalidation.

## Testing Expectations
- Run relevant pytest targets; include integration tests for adapters when DSNs/drivers are required and available.
- Document test commands and results in your summary if you cannot run certain suites (e.g., missing drivers).

## Anti-Patterns To Avoid (seen in repo)
- Hard-coded SQLite placeholders in cross-dialect code (`Session.get` bug) — always use dialect placeholders.
- Adding global `# mypy: ignore-errors` instead of fixing types.
- Assuming context-bound sessions exist without entering `with session:` — leads to runtime errors in m2m/managers.
- Skipping cache invalidation when mutating relations.
