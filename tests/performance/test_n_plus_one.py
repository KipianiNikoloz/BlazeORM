import logging

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.persistence import Session


def create_table(session: Session) -> None:
    session.execute(
        'CREATE TABLE IF NOT EXISTS "perf_user" (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)'
    )
    session.execute('DELETE FROM "perf_user"')
    for idx in range(1, 6):
        session.execute('INSERT INTO "perf_user" (name) VALUES (?)', (f"user-{idx}",))


def test_session_emits_n_plus_one_warning(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger="blazeorm.persistence.session")
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'perf.db'}")
    session = Session(adapter, connection_config=config, performance_threshold=4)
    create_table(session)

    for idx in range(1, 6):
        session.execute('SELECT name FROM "perf_user" WHERE id = ?', (idx,))

    assert any("Potential N+1 detected" in record.message for record in caplog.records)
    stats = session.query_stats()
    assert stats
    session.close()
