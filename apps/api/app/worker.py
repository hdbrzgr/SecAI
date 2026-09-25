"""ARQ worker entrypoint: `arq app.worker.WorkerSettings`."""

import uuid
from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.scanning.pipeline import run_scan as run_scan_pipeline


async def ping(ctx: dict[str, Any]) -> str:
    return "pong"


async def run_scan(ctx: dict[str, Any], scan_id: str) -> None:
    await run_scan_pipeline(get_sessionmaker(), uuid.UUID(scan_id))


class WorkerSettings:
    functions: ClassVar[list[Any]] = [ping, run_scan]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
    job_timeout = 60 * 60
    # A scan must never run twice because a worker restarted mid-way.
    max_tries = 1
