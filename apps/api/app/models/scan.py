import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, JSONType, TimestampMixin, utcnow


class ScanKind(enum.StrEnum):
    dast = "dast"
    sast = "sast"


class ScanStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class Severity(enum.StrEnum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


def _enum(e: type[enum.StrEnum]) -> Enum:
    return Enum(e, native_enum=False, length=20)


class Scan(IdMixin, TimestampMixin, Base):
    __tablename__ = "scans"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("targets.id", ondelete="CASCADE"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    kind: Mapped[ScanKind] = mapped_column(_enum(ScanKind))
    status: Mapped[ScanStatus] = mapped_column(_enum(ScanStatus), default=ScanStatus.queued)
    profile: Mapped[str] = mapped_column(String(50), default="baseline")
    progress: Mapped[int] = mapped_column(default=0)
    current_step: Mapped[str | None] = mapped_column(String(200))
    # Counts per severity, score, grade and per-tool results, filled when the scan ends.
    summary: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    # The user's confirmation that they may scan this target, recorded per scan.
    attested_at: Mapped[datetime | None]
    attested_ip: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    error: Mapped[str | None] = mapped_column(Text)


class Finding(IdMixin, Base):
    """One normalized finding. Every scanner's output is converted into this shape."""

    __tablename__ = "findings"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True
    )
    # Stable hash of (rule, location) used to dedupe across tools and diff across scans.
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    tool: Mapped[str] = mapped_column(String(50))
    rule_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500))
    severity: Mapped[Severity] = mapped_column(_enum(Severity))
    cwe: Mapped[str | None] = mapped_column(String(20))
    location: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    evidence: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    references: Mapped[list[str]] = mapped_column(JSONType, default=list)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
