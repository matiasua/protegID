"""Cliente y health check básico de Redis."""

from functools import lru_cache

import redis

from app.core.settings import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    redis_url = get_settings().redis_url
    if not redis_url:
        raise RuntimeError("REDIS_URL is not configured")

    return redis.Redis.from_url(redis_url)


def ping_redis() -> bool:
    return bool(get_redis_client().ping())
