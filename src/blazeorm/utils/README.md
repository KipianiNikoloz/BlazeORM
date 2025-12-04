Utilities
=========

What Lives Here
---------------
- `logging.py`: Structured logging setup, correlation ID support, timing helper `time_call`.
- `performance.py`: `PerformanceTracker` for SQL timing, N+1 detection, metrics summary.
- `naming.py` and helpers: camel/snake conversions.

Key Behaviors
-------------
- `time_call` wraps execution with timing + structured logs (used by adapters/session).
- `PerformanceTracker` tracks executed SQL signatures; warns on repeated parameterized statements over a threshold.
- Logging utilities integrate with adapters and session for consistent outputs.

Testing References
------------------
- `tests/utils/test_logging.py`, `tests/utils/test_performance_tracker.py`, `tests/performance/test_n_plus_one.py`.

