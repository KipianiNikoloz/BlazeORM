# Known Gaps (Actionable)
- Typing laxity: mypy remains non-strict; optional driver imports are still ignored via overrides. Further tightening (e.g., stricter Any usage, return types) remains.
- No PyPI distribution pipeline yet; install-from-pip flow is not available until publish workflow is implemented.
