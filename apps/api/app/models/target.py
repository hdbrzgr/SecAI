import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class VerificationMethod(enum.StrEnum):
    dns_txt = "dns_txt"
    well_known_file = "well_known_file"
    meta_tag = "meta_tag"


class Target(IdMixin, TimestampMixin, Base):
    """A website the organization wants to scan. Active scans require verified ownership."""

    __tablename__ = "targets"
    __table_args__ = (UniqueConstraint("org_id", "hostname"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(2048))
    hostname: Mapped[str] = mapped_column(String(253), index=True)
    verification_token: Mapped[str] = mapped_column(String(64))
    verification_method: Mapped[VerificationMethod | None] = mapped_column(
        Enum(VerificationMethod, native_enum=False, length=20)
    )
    verified_at: Mapped[datetime | None]
    last_verification_check_at: Mapped[datetime | None]
