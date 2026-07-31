from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.cache import InMemoryCache
from blazeorm.core import Model, StringField
from blazeorm.persistence import Session


class Note(Model):
    text = StringField(nullable=False)


def make_session(tmp_path, *, cache=None):
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'transaction-state.db'}")
    session = Session(SQLiteAdapter(), connection_config=config, cache_backend=cache)
    session.execute(
        'CREATE TABLE IF NOT EXISTS "note" '
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL)"
    )
    session.commit()
    return session


def test_rollback_restores_flushed_update_to_transaction_entry_state(tmp_path):
    session = make_session(tmp_path)
    note = Note(text="Before")
    session.bulk_create([note])

    session.begin()
    note.text = "During"
    session.mark_dirty(note)
    session.flush()
    assert note._initial_state["text"] == "During"
    session.rollback()

    assert note.text == "Before"
    assert note._initial_state["text"] == "Before"
    assert note.is_dirty() is False
    assert note._persisted is True
    assert session.identity_map.get(Note, note.id) is note


def test_rollback_restores_staged_new_instance_after_flush(tmp_path):
    session = make_session(tmp_path)
    note = Note(text="New")
    session.add(note)
    session.begin()

    session.flush()
    assert note.id == 1
    assert note._persisted is True
    session.rollback()

    assert "id" not in note._field_values
    assert note._persisted is False
    assert note in session.unit_of_work.new
    assert note not in session.identity_map.values()
    assert session.execute('SELECT COUNT(*) FROM "note"').fetchone()[0] == 0


def test_rollback_restores_flushed_delete_lifecycle_and_identity(tmp_path):
    session = make_session(tmp_path)
    note = Note(text="Keep")
    session.bulk_create([note])

    session.begin()
    session.delete(note)
    session.flush()
    assert note._persisted is False
    assert session.identity_map.get(Note, note.id) is None
    session.rollback()

    assert note._persisted is True
    assert session.identity_map.get(Note, note.id) is note
    assert session.execute('SELECT text FROM "note" WHERE id = 1').fetchone()[0] == "Keep"


def test_rollback_restores_new_instance_registered_after_begin(tmp_path):
    session = make_session(tmp_path)
    note = Note(text="Late")
    session.begin()

    session.add(note)
    session.flush()
    assert note.id == 1
    session.rollback()

    assert note._field_values == {"text": "Late"}
    assert note._persisted is False
    assert note not in session.unit_of_work.new
    assert note not in session.identity_map.values()


def test_nested_rollback_restores_inner_entry_then_outer_commits(tmp_path):
    session = make_session(tmp_path)
    note = Note(text="Before")
    session.bulk_create([note])
    session.begin()
    note.text = "Outer"
    session.mark_dirty(note)
    session.flush()
    session.begin()
    note.text = "Inner"
    session.mark_dirty(note)
    session.flush()

    session.rollback()

    assert note.text == "Outer"
    assert session.transaction_manager.depth == 1
    session.commit()
    assert session.execute('SELECT text FROM "note" WHERE id = 1').fetchone()[0] == "Outer"


def test_outer_rollback_restores_state_after_inner_commit(tmp_path):
    session = make_session(tmp_path)
    note = Note(text="Before")
    session.bulk_create([note])
    session.begin()
    note.text = "Outer"
    session.mark_dirty(note)
    session.flush()
    session.begin()
    note.text = "Inner"
    session.mark_dirty(note)
    session.flush()
    session.commit()

    session.rollback()

    assert note.text == "Before"
    assert note.is_dirty() is False
    assert session.execute('SELECT text FROM "note" WHERE id = 1').fetchone()[0] == "Before"


def test_rollback_rebuilds_identity_and_second_level_cache(tmp_path):
    cache = InMemoryCache()
    session = make_session(tmp_path, cache=cache)
    note = Note(text="Cached")
    session.bulk_create([note])
    session.begin()
    note.text = "Uncommitted"
    session.mark_dirty(note)
    session.flush()
    assert cache.get(Note, note.id)["text"] == "Uncommitted"

    session.rollback()

    assert session.identity_map.get(Note, note.id) is note
    assert cache.get(Note, note.id)["text"] == "Cached"
