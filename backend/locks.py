from collections.abc import Generator
from contextlib import contextmanager

import weave

from backend.redis_client import get_redis


@contextmanager
def incident_lock(
    incident_id: str,
    action: str,
    timeout: int = 60,
    blocking_timeout: int = 1,
) -> Generator[bool, None, None]:
    lock = get_redis().lock(
        f"lock:incident:{incident_id}:{action}",
        timeout=timeout,
        blocking_timeout=blocking_timeout,
    )
    acquired = lock.acquire(blocking=True)
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()


@weave.op()
def lock_available(incident_id: str, action: str) -> bool:
    key = f"lock:incident:{incident_id}:{action}"
    return not bool(get_redis().exists(key))

