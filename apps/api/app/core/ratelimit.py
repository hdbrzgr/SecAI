from redis.asyncio import Redis


async def hit(redis: Redis, key: str, limit: int, window_seconds: int) -> bool:
    """Fixed-window counter. Returns True while the caller is still under the limit."""
    full_key = f"ratelimit:{key}"
    count = await redis.incr(full_key)
    if count == 1:
        await redis.expire(full_key, window_seconds)
    return count <= limit


async def reset(redis: Redis, key: str) -> None:
    await redis.delete(f"ratelimit:{key}")
