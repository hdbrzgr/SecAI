import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class OrgRole(enum.StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Organization(IdMixin, TimestampMixin, Base):
    """A workspace. Targets, scans and quotas belong to an organization."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class Membership(IdMixin, TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("org_id", "user_id"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[OrgRole] = mapped_column(Enum(OrgRole, native_enum=False, length=20))

    organization: Mapped[Organization] = relationship(back_populates="memberships")
