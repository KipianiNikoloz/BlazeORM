import logging

from blazeorm.utils.performance import PerformanceTracker
from blazeorm.utils import get_logger


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
