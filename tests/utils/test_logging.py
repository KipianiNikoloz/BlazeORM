import logging
import re

from blazeorm.utils.logging import get_logger, set_correlation_id, get_correlation_id, time_call


def test_correlation_id_round_trip():
    token = set_correlation_id("test-token")
    assert token == "test-token"
    assert get_correlation_id() == "test-token"


def test_time_call_logs_duration(caplog):
    logger = get_logger("tests.logging")
    # ensure handler exists and capturing
    caplog.set_level(logging.DEBUG, logger=logger.name)
    with time_call("unit-test", logger, threshold_ms=0):
        pass
    messages = [record.message for record in caplog.records if record.name == logger.name]
    assert any("unit-test took" in message for message in messages)
