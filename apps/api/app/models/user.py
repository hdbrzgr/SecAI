import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin, utcnow


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    # Instance administrator (the first account created on an instance).
    is_superuser: Mapped[bool] = mapped_column(default=False)
    email_verified_at: Mapped[datetime | None]

    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    # TOTP secrets are encrypted with a key derived from SECAI_SECRET_KEY.
    totp_secret_enc: Mapped[str | None] = mapped_column(String(255))
    totp_pending_secret_enc: Mapped[str | None] = mapped_column(String(255))
    # Last accepted TOTP time-step, so a code can't be replayed.
    totp_last_counter: Mapped[int | None]

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(IdMixin, Base):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # False while a login is waiting for its second factor.
    mfa_verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))

    user: Mapped[User] = relationship(back_populates="sessions")
