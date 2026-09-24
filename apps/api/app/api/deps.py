from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import Settings, get_settings
from app.core.security import hash_token
from app.db.session import get_db
from app.models import User, UserSession


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def client_ip(request: Request) -> str:
    # Behind a reverse proxy, uvicorn's --proxy-headers/--forwarded-allow-ips set this correctly.
    return request.client.host if request.client else "unknown"


@dataclass
class AuthContext:
    session: UserSession
    user: User


def _as_aware(dt: datetime) -> datetime:
    # SQLite (tests) returns naive datetimes; Postgres returns aware ones.
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def _load_session(
    request: Request, db: AsyncSession, settings: Settings
) -> AuthContext | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    session = await db.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user))
        .where(UserSession.token_hash == hash_token(token))
    )
    if session is None:
        return None
    now = datetime.now(UTC)
    idle_limit = _as_aware(session.last_seen_at) + timedelta(minutes=settings.session_idle_minutes)
    if _as_aware(session.expires_at) <= now or idle_limit <= now or not session.user.is_active:
        await db.delete(session)
        await db.commit()
        return None
    if now - _as_aware(session.last_seen_at) > timedelta(minutes=1):
        session.last_seen_at = now
        await db.commit()
    return AuthContext(session=session, user=session.user)


async def get_pending_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    """A session that exists but may still be waiting for its second factor."""
    ctx = await _load_session(request, db, settings)
    if ctx is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return ctx


async def get_auth(ctx: AuthContext = Depends(get_pending_auth)) -> AuthContext:
    if not ctx.session.mfa_verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Two-factor authentication required")
    return ctx


async def get_current_user(ctx: AuthContext = Depends(get_auth)) -> User:
    return ctx.user
