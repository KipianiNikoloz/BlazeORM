# Instructions Folder

Purpose: be the single source of truth for BlazeORM goals, constraints, current state, plans, and standards. Agents must obey these files before changing code.

How to use:
- Read `project_goal.md`, `constraints.md`, `architecture.md`, and `coding_standards.md` before any task.
- Read `current_state.md` to understand reality (features, maturity, known issues, branch/CI facts).
- Read `plan.md` to pick the next step; do not invent work.
- After implementing a step, update `current_state.md`, `known_gaps.md`, and `plan.md` if scope/status changes.

Workflow (always in this order):
1. Understand scope: restate the ask; confirm it fits `project_goal.md` and `constraints.md`.
2. Inspect relevant code/tests; assume code/test behavior is ground truth.
3. Plan the change using `plan.md`; adjust the plan explicitly if needed.
4. Implement using `coding_standards.md` and `architecture.md`; keep cross-dialect behavior intact.
5. Test (unit + integration when applicable); never skip silently.
6. Update documentation: `current_state.md`, `known_gaps.md`, `plan.md` as appropriate.
7. Summarize changes, risks, and testing done.

Do Not Assume:
- Do not hallucinate requirements. If it is not in this folder or the code/tests, it is not real.
- Do not rely on unstated defaults; prefer explicit parameters and errors.
- Do not assume SQLite-only behavior applies to Postgres/MySQL.
