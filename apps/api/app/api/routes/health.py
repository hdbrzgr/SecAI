from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_redis
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(
    db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)
) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ready"}
