import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, JSONType, utcnow


class InstanceSettings(Base):
    """Settings an instance admin can change at runtime. One row (id=1), created on first
    read from the SECAI_* environment defaults."""

    __tablename__ = "instance_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_open: Mapped[bool]
    scans_per_day_per_org: Mapped[int]
    max_targets_per_org: Mapped[int]
    # Kill switch: no new scans start and queued scans don't run while it's on.
    scanning_paused: Mapped[bool] = mapped_column(default=False)
    scanning_paused_reason: Mapped[str | None] = mapped_column(String(300))
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class BlockedDomain(IdMixin, Base):
    """A domain (and its subdomains) that nobody on this instance may add or scan."""

    __tablename__ = "blocked_domains"

    domain: Mapped[str] = mapped_column(String(253), unique=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class AuditEvent(IdMixin, Base):
    """Who did what: scan attestations, ownership proofs, admin changes, account security."""

    __tablename__ = "audit_events"

    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    subject: Mapped[str | None] = mapped_column(String(300))
    ip: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    note: Mapped[str | None] = mapped_column(Text)
