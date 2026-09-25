"""Periodic housekeeping run by the worker (see WorkerSettings.cron_jobs)."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.models import ActionToken, Scan, ScanStatus, UserSession

log = logging.getLogger(__name__)
JOB_TIMEOUT = timedelta(hours=1)  # keep in step with WorkerSettings.job_timeout


async def cleanup_expired(sessionmaker: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    """Delete expired or idle sessions and spent emailed tokens."""
    now = datetime.now(UTC)
    idle = now - timedelta(minutes=get_settings().session_idle_minutes)
    async with sessionmaker() as db:
        sessions = await db.execute(
            delete(UserSession).where(
                or_(UserSession.expires_at < now, UserSession.last_seen_at < idle)
            )
        )
        tokens = await db.execute(
            delete(ActionToken).where(
                or_(
                    ActionToken.expires_at < now - timedelta(days=1),
                    ActionToken.used_at.is_not(None),
                )
            )
        )
        await db.commit()
    return {"sessions": sessions.rowcount or 0, "tokens": tokens.rowcount or 0}


async def reap_stuck_scans(sessionmaker: async_sessionmaker[AsyncSession]) -> int:
    """Fail scans a crashed or restarted worker left behind, so websites can be scanned again."""
    now = datetime.now(UTC)
    async with sessionmaker() as db:
        stuck = (
            await db.scalars(
                select(Scan.id).where(
                    or_(
                        (Scan.status == ScanStatus.running)
                        & (Scan.started_at < now - JOB_TIMEOUT - timedelta(minutes=10)),
                        (Scan.status == ScanStatus.queued)
                        & (Scan.created_at < now - timedelta(hours=6)),
                    )
                )
            )
        ).all()
        if stuck:
            await db.execute(
                update(Scan)
                .where(Scan.id.in_(stuck))
                .values(
                    status=ScanStatus.failed,
                    error="The scan stopped unexpectedly (the worker was interrupted). "
                    "Run it again.",
                    finished_at=now,
                    current_step=None,
                )
            )
            await db.commit()
            log.warning("Marked %d stuck scans as failed", len(stuck))
    return len(stuck)
