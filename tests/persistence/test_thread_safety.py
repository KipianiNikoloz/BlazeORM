import threading

from blazeorm.adapters import ConnectionConfig, SQLiteAdapter
from blazeorm.core import IntegerField, Model
from blazeorm.persistence import IdentityMap, Session


class ThreadUser(Model):
    id = IntegerField(primary_key=True)


def test_identity_map_thread_safety():
    identity_map = IdentityMap()
    errors: list[Exception] = []
    barrier = threading.Barrier(5)

    def worker(offset: int) -> None:
        try:
            barrier.wait()
            for idx in range(200):
                instance = ThreadUser(id=offset * 1000 + idx)
                identity_map.add(instance)
                identity_map.get(ThreadUser, instance.id)
                identity_map.remove(instance)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []


def test_session_query_stats_thread_safety(tmp_path):
    adapter = SQLiteAdapter()
    config = ConnectionConfig(url=f"sqlite:///{tmp_path / 'threadsafe.db'}")
    session = Session(adapter, connection_config=config)
    errors: list[Exception] = []
    barrier = threading.Barrier(4)

    def worker() -> None:
        try:
            barrier.wait()
            for _ in range(50):
                session.query_stats()
                session.export_query_stats()
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    session.close()
    assert errors == []
