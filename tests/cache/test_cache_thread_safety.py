import threading

from blazeorm.cache import InMemoryCache
from blazeorm.core import IntegerField, Model


class CacheUser(Model):
    id = IntegerField(primary_key=True)


def test_in_memory_cache_thread_safety():
    cache = InMemoryCache()
    errors: list[Exception] = []
    barrier = threading.Barrier(4)

    def worker(offset: int) -> None:
        try:
            barrier.wait()
            for idx in range(200):
                pk = offset * 1000 + idx
                cache.set(CacheUser, pk, {"id": pk})
                cache.get(CacheUser, pk)
                cache.delete(CacheUser, pk)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
