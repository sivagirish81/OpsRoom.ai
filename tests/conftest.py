import os

# Keep tests isolated from demo data on db 0.
os.environ.setdefault("REDIS_URL", os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15"))

import pytest
import redis

TEST_REDIS_URL = os.environ["REDIS_URL"]


@pytest.fixture(autouse=True)
def reset_redis_cache():
    from backend.config import get_settings
    from backend.redis_client import get_redis

    get_settings.cache_clear()
    get_redis.cache_clear()
    yield
    get_settings.cache_clear()
    get_redis.cache_clear()


@pytest.fixture
def redis_client():
    client = redis.Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis is not available for integration tests")
    yield client
