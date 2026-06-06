from functools import lru_cache

import redis
import weave

from backend.config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


@weave.op()
def redis_healthcheck() -> bool:
    return bool(get_redis().ping())

