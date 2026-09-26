"""Runtime instance settings, the domain blocklist and the audit log."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import AuditEvent, BlockedDomain, InstanceSettings


async def get_instance_settings(db: AsyncSession, settings: Settings) -> InstanceSettings:
    row = await db.get(InstanceSettings, 1)
    if row is None:
        row = InstanceSettings(
            id=1,
            registration_open=settings.allow_registration,
            scans_per_day_per_org=settings.scans_per_day_per_org,
            max_targets_per_org=settings.max_targets_per_org,
            scanning_paused=False,
        )
        db.add(row)
        await db.flush()
    return row


def domain_candidates(hostname: str) -> list[str]:
    """shop.example.com -> [shop.example.com, example.com, com]"""
    labels = hostname.lower().rstrip(".").split(".")
    return [".".join(labels[i:]) for i in range(len(labels))]


async def blocked_by(db: AsyncSession, hostname: str) -> BlockedDomain | None:
    return await db.scalar(
        select(BlockedDomain).where(BlockedDomain.domain.in_(domain_candidates(hostname))).limit(1)
    )


def audit(
    db: AsyncSession,
    action: str,
    *,
    actor_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None,
    subject: str | None = None,
    ip: str | None = None,
    **details: Any,
) -> None:
    """Record an event in the current transaction; it's saved with the caller's commit."""
    db.add(
        AuditEvent(
            action=action, actor_id=actor_id, org_id=org_id, subject=subject, ip=ip, details=details
        )
    )
