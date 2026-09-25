"""ARQ worker entrypoint: `arq app.worker.WorkerSettings`."""

import uuid
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.core import mail
from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.maintenance import cleanup_expired, reap_stuck_scans
from app.scanning.pipeline import run_scan as run_scan_pipeline


async def ping(ctx: dict[str, Any]) -> str:
    return "pong"


async def send_email(
    ctx: dict[str, Any],
    to: str,
    subject: str,
    paragraphs: list[str],
    action: tuple[str, str] | list[str] | None = None,
) -> bool:
    return await mail.send(
        mail.build_message(to, subject, paragraphs, tuple(action) if action else None)
    )


async def run_scan(ctx: dict[str, Any], scan_id: str) -> None:
    await run_scan_pipeline(get_sessionmaker(), uuid.UUID(scan_id))


async def housekeeping(ctx: dict[str, Any]) -> dict[str, int]:
    removed = await cleanup_expired(get_sessionmaker())
    removed["stuck_scans"] = await reap_stuck_scans(get_sessionmaker())
    return removed


class WorkerSettings:
    functions: ClassVar[list[Any]] = [ping, run_scan, send_email]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
    job_timeout = 60 * 60
    # A scan must never run twice because a worker restarted mid-way.
    max_tries = 1
    cron_jobs: ClassVar[list[Any]] = [
        cron(housekeeping, minute=set(range(0, 60, 10)), run_at_startup=True, unique=True)
    ]
