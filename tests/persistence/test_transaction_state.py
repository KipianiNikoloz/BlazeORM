from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import Model, StringField
from blazeorm.persistence import Session


class Note(Model):
    text = StringField(nullable=False)


def make_session(tmp_path):
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'transaction-state.db'}")
    session = Session(SQLiteAdapter(), connection_config=config)
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
