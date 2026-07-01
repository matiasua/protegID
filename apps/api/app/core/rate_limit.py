"""Rate limiting básico con Redis."""

from hashlib import sha256

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.core.redis import get_redis_client

RATE_LIMIT_EXCEEDED_DETAIL = "Too many requests. Try again later."


def get_client_ip(request: Request) -> str:
    # Producción detrás de proxy requiere trusted proxy antes de usar X-Forwarded-For.
    return request.client.host if request.client else "unknown"


def hash_rate_limit_value(value: str) -> str:
    return sha256(value.strip().lower().encode("utf-8")).hexdigest()


def check_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    try:
        redis_client = get_redis_client()
        count = int(redis_client.incr(key))
        if count == 1:
            redis_client.expire(key, window_seconds)
        elif redis_client.ttl(key) == -1:
            redis_client.expire(key, window_seconds)
    except (RedisError, RuntimeError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limit service unavailable.",
        ) from error

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=RATE_LIMIT_EXCEEDED_DETAIL,
        )
