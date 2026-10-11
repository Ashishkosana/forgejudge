"""Shared API service and Redis dependencies."""

from redis.asyncio import Redis

from backend.common.redis import create_redis_client
from backend.services.problems import ProblemsService
from backend.services.submissions import SubmissionsService

redis_client: Redis = create_redis_client()
problems_service = ProblemsService()
submissions_service = SubmissionsService()


def get_redis() -> Redis:
    return redis_client
