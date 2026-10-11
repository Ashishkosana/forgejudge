"""Redis-backed fixed-window rate limiting for credential endpoints."""

import hashlib

from redis.asyncio import Redis
from redis.exceptions import RedisError

_INCREMENT_WITH_EXPIRY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local account_count = redis.call('INCR', KEYS[2])
if account_count == 1 then
  redis.call('EXPIRE', KEYS[2], ARGV[2])
end
return {count, account_count}
"""


class RateLimitUnavailableError(Exception):
    pass


async def consume_auth_attempt(
    redis: Redis,
    source: str,
    *,
    identity: str,
    source_limit: int = 30,
    identity_limit: int = 5,
) -> bool:
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    identity_hash = hashlib.sha256(identity.strip().lower().encode("utf-8")).hexdigest()
    source_key = f"forgejudge:auth-rate:source:{source_hash}"
    identity_key = f"forgejudge:auth-rate:identity:{identity_hash}"
    try:
        counts = await redis.eval(
            _INCREMENT_WITH_EXPIRY, 2, source_key, identity_key, 60, 60
        )
    except (RedisError, TimeoutError) as exc:
        raise RateLimitUnavailableError from exc
    return int(counts[0]) <= source_limit and int(counts[1]) <= identity_limit
