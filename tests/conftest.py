from collections.abc import Generator
from typing import Any

import pytest

from blazeorm.persistence import Session


@pytest.fixture(autouse=True)
def close_sessions_created_by_test(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Keep SQLite and optional-driver connections scoped to each test."""
    sessions: list[Session] = []
    original_init = Session.__init__

    def tracking_init(self: Session, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        sessions.append(self)

    monkeypatch.setattr(Session, "__init__", tracking_init)
    yield
    for session in reversed(sessions):
        session.close()
