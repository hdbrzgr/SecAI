"""ARQ worker entrypoint: `arq app.worker.WorkerSettings`. Scan jobs are added in Phase 1."""

from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings


async def ping(ctx: dict[str, Any]) -> str:
    return "pong"


class WorkerSettings:
    functions: ClassVar[list[Any]] = [ping]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
    job_timeout = 60 * 60
