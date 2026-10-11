"""Redis-backed fixed-window rate limiting for credential endpoints."""

import hashlib

from redis.asyncio import Redis
from redis.exceptions import RedisError

_INCREMENT_WITH_EXPIRY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


class RateLimitUnavailableError(Exception):
    pass


async def consume_auth_attempt(redis: Redis, source: str, *, limit: int = 10) -> bool:
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    key = f"forgejudge:auth-rate:{source_hash}"
    try:
        count = await redis.eval(_INCREMENT_WITH_EXPIRY, 1, key, 60)
    except (RedisError, TimeoutError) as exc:
        raise RateLimitUnavailableError from exc
    return int(count) <= limit
