"""Redis client construction for API and worker processes."""

from redis.asyncio import Redis

from backend.common.config import settings


def create_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)
