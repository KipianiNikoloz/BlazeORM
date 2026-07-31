from datetime import datetime, timezone

import pytest

from blazeorm import DoesNotExist
from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.cache import InMemoryCache
from blazeorm.core import DateTimeField, Model, StringField
from blazeorm.persistence import Session


class Document(Model):
    title = StringField(nullable=False)
    created_at = DateTimeField(auto_now_add=True, nullable=False)
    updated_at = DateTimeField(auto_now=True, nullable=False)


def make_session(tmp_path, *, cache_backend=None):
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'managed.db'}")
    session = Session(SQLiteAdapter(), connection_config=config, cache_backend=cache_backend)
    session.execute(
        'CREATE TABLE IF NOT EXISTS "document" '
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
        "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    return session


def test_managed_timestamps_apply_on_insert_and_update(tmp_path):
    session = make_session(tmp_path)
    old = datetime(2000, 1, 1, tzinfo=timezone.utc)
    document = Document(title="Draft", created_at=old, updated_at=old)

    document.save(session=session)
    session.commit()
    created_at = document.created_at
    first_updated_at = document.updated_at

    assert created_at > old
    assert first_updated_at > old
    assert created_at.tzinfo is timezone.utc
    assert first_updated_at.tzinfo is timezone.utc

    document.title = "Published"
    document.save(session=session)
    session.commit()

    assert document.created_at == created_at
    assert document.updated_at > first_updated_at


def test_datetime_field_hydrates_iso_text(tmp_path):
    session = make_session(tmp_path)
    timestamp = "2026-07-31T14:30:00+00:00"
    session.execute(
        'INSERT INTO "document" (title, created_at, updated_at) VALUES (?, ?, ?)',
        ("Stored", timestamp, timestamp),
    )

    document = session.get(Document, id=1)

    assert document.created_at == datetime(2026, 7, 31, 14, 30, tzinfo=timezone.utc)
    assert document.updated_at == datetime(2026, 7, 31, 14, 30, tzinfo=timezone.utc)


def test_refresh_reloads_same_instance_and_resets_state(tmp_path):
    cache = InMemoryCache()
    session = make_session(tmp_path, cache_backend=cache)
    document = Document(title="Original")
    document.save(session=session)
    session.commit()
    document.title = "Local edit"
    document._related_cache["authors"] = [object()]
    session.mark_dirty(document)
    session.execute('UPDATE "document" SET title = ? WHERE id = ?', ("Database", document.id))

    refreshed = session.refresh(document)

    assert refreshed is document
    assert document.title == "Database"
    assert document.is_dirty() is False
    assert document._related_cache == {}
    assert document not in session.unit_of_work.dirty
    assert session.identity_map.get(Document, document.id) is document
    assert cache.get(Document, document.id)["title"] == "Database"


def test_refresh_rejects_new_and_deleted_instances(tmp_path):
    session = make_session(tmp_path)
    new_document = Document(title="New")

    with pytest.raises(ValueError, match="persisted"):
        session.refresh(new_document)

    deleted = Document(title="Delete")
    deleted.save(session=session)
    session.commit()
    deleted.delete(session=session)
    session.commit()

    with pytest.raises(ValueError, match="persisted"):
        session.refresh(deleted)


def test_refresh_raises_when_database_row_is_missing(tmp_path):
    session = make_session(tmp_path)
    document = Document(title="Missing")
    document.save(session=session)
    session.commit()
    session.execute('DELETE FROM "document" WHERE id = ?', (document.id,))

    with pytest.raises(DoesNotExist, match="Document"):
        session.refresh(document)
