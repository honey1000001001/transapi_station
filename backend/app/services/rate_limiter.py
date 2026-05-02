import logging
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based sliding window rate limiter using sorted sets."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rpm(self, key_id: str, rpm_limit: int) -> bool:
        """Check requests per minute. Returns True if within limit."""
        if rpm_limit <= 0:
            return True

        if self.redis is None:
            return True

        now = time.time()
        window_start = now - 60
        redis_key = f"ratelimit:{key_id}:rpm"

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(redis_key, "-inf", window_start)
        pipe.zadd(redis_key, {str(now): now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, 120)
        results = await pipe.execute()

        count = results[2]
        if count > rpm_limit:
            # Remove the entry we just added since we're over limit
            await self.redis.zrem(redis_key, str(now))
            return False
        return True

    async def check_tpm(self, key_id: str, token_count: int, tpm_limit: int) -> bool:
        """Check tokens per minute. Returns True if within limit."""
        if tpm_limit <= 0:
            return True

        if self.redis is None:
            return True

        now = time.time()
        window_start = now - 60
        redis_key = f"ratelimit:{key_id}:tpm"

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(redis_key, "-inf", window_start)
        # Store token count as member with timestamp as score
        member = f"{now}:{token_count}"
        pipe.zadd(redis_key, {member: now})
        pipe.zrange(redis_key, 0, -1, withscores=True)
        pipe.expire(redis_key, 120)
        results = await pipe.execute()

        members = results[2]
        total_tokens = sum(int(m.decode().split(":")[1]) if isinstance(m, bytes) else m.split(":")[1] for m, _ in members)

        if total_tokens > tpm_limit:
            await self.redis.zrem(redis_key, member)
            return False
        return True
