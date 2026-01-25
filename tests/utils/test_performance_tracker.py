import logging

import pytest

from blazeorm.utils import get_logger
from blazeorm.utils.performance import PerformanceTracker, resolve_slow_query_ms


def test_performance_tracker_records_summary(caplog):
    caplog.set_level(logging.WARNING, logger="blazeorm.tests.performance")
    tracker = PerformanceTracker(
        get_logger("tests.performance"), n_plus_one_threshold=3, sample_size=2
    )
    for i in range(3):
        tracker.record("SELECT * FROM foo WHERE id = ?", [i], 1.5)
    assert any("Potential N+1 detected" in rec.message for rec in caplog.records)

    summary = tracker.summary()
    assert summary[0]["count"] == 3
    assert summary[0]["distinct_params"] >= 2


def test_performance_tracker_reset():
    tracker = PerformanceTracker(get_logger("tests.performance"), n_plus_one_threshold=2)
    tracker.record("SELECT 1", [], 0.5)
    tracker.reset()
    assert tracker.summary() == []


def test_performance_tracker_export_includes_samples():
    tracker = PerformanceTracker(
        get_logger("tests.performance"), n_plus_one_threshold=3, sample_size=2
    )
    tracker.record("SELECT * FROM foo WHERE id = ?", ["one"], 1.0)
    tracker.record("SELECT * FROM foo WHERE id = ?", ["two"], 1.0)
    exported = tracker.export(include_samples=True)
    assert exported[0]["count"] == 2
    assert "samples" in exported[0]
    assert len(exported[0]["samples"]) == 2


def test_resolve_slow_query_ms_uses_env(monkeypatch):
    monkeypatch.setenv("BLAZE_SLOW_QUERY_MS", "150")
    assert resolve_slow_query_ms(default=200, override=None) == 150


def test_resolve_slow_query_ms_override_wins(monkeypatch):
    monkeypatch.setenv("BLAZE_SLOW_QUERY_MS", "150")
    assert resolve_slow_query_ms(default=200, override=75) == 75


def test_resolve_slow_query_ms_invalid_env(monkeypatch):
    monkeypatch.setenv("BLAZE_SLOW_QUERY_MS", "nope")
    with pytest.raises(ValueError):
        resolve_slow_query_ms(default=200, override=None)


def test_resolve_slow_query_ms_rejects_negative():
    with pytest.raises(ValueError):
        resolve_slow_query_ms(default=200, override=-1)
