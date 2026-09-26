"""Email verification and password management."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, _as_aware, client_ip, get_auth, get_redis
from app.core import ratelimit
from app.core.config import Settings, get_settings
from app.core.instance import audit, get_instance_settings
from app.core.mail import smtp_configured
from app.core.security import hash_password, hash_token, verify_password
from app.db.session import get_db
from app.models import ActionToken, User, UserSession
from app.scanning.queue import Enqueue, get_enqueue
from app.schemas.auth import (
    ChangePasswordIn,
    ForgotPasswordIn,
    PublicConfig,
    ResetPasswordIn,
    TokenIn,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["account"])

VERIFY = "verify_email"
RESET = "reset_password"
LIFETIME = {VERIFY: timedelta(hours=48), RESET: timedelta(minutes=30)}


async def issue_token(db: AsyncSession, user: User, purpose: str) -> str:
    # One live token per purpose: issuing a new one invalidates older links.
    await db.execute(
        delete(ActionToken).where(ActionToken.user_id == user.id, ActionToken.purpose == purpose)
    )
    token = secrets.token_urlsafe(32)
    db.add(
        ActionToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + LIFETIME[purpose],
        )
    )
    return token


async def consume_token(db: AsyncSession, token: str, purpose: str) -> User:
    row = await db.scalar(
        select(ActionToken).where(
            ActionToken.token_hash == hash_token(token), ActionToken.purpose == purpose
        )
    )
    if row is None or row.used_at is not None or _as_aware(row.expires_at) < datetime.now(UTC):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This link has expired or was already used. Request a new one.",
        )
    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This link is no longer valid")
    row.used_at = datetime.now(UTC)
    return user


async def send_verification(
    db: AsyncSession, user: User, settings: Settings, enqueue: Enqueue
) -> None:
    token = await issue_token(db, user, VERIFY)
    await enqueue(
        "send_email",
        user.email,
        "Confirm your email address for SecAI",
        [
            f"Hi{' ' + user.name if user.name else ''},",
            "Confirm this email address to start adding websites to SecAI. "
            "The link works for 48 hours.",
            "If you didn't create a SecAI account, you can ignore this email.",
        ],
        ("Confirm email address", f"{settings.web_origin.rstrip('/')}/verify-email?token={token}"),
    )


@router.get("/config", response_model=PublicConfig)
async def public_config(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> PublicConfig:
    instance = await get_instance_settings(db, settings)
    first_user = (await db.scalar(select(func.count()).select_from(User))) == 0
    await db.commit()
    return PublicConfig(
        registration_open=instance.registration_open or first_user,
        email_enabled=smtp_configured(),
    )


@router.post("/email/verify/request", status_code=status.HTTP_202_ACCEPTED)
async def request_verification(
    ctx: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    enqueue: Enqueue = Depends(get_enqueue),
) -> dict[str, str]:
    user = ctx.user
    if user.email_verified:
        return {"status": "already_verified"}
    if not smtp_configured():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email isn't configured on this instance")
    if not await ratelimit.hit(redis, f"verify-email:{user.id}", 3, 60 * 60):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many emails sent, try later")
    await send_verification(db, user, settings, enqueue)
    await db.commit()
    return {"status": "sent"}


@router.post("/email/verify", response_model=UserOut)
async def verify_email(body: TokenIn, request: Request, db: AsyncSession = Depends(get_db)) -> User:
    user = await consume_token(db, body.token, VERIFY)
    user.email_verified_at = datetime.now(UTC)
    audit(db, "user.email_verified", actor_id=user.id, subject=user.email, ip=client_ip(request))
    await db.commit()
    return user


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    body: ForgotPasswordIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    enqueue: Enqueue = Depends(get_enqueue),
) -> dict[str, str]:
    if not smtp_configured():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Password reset by email isn't available on this instance. Ask the administrator.",
        )
    window = settings.login_rate_limit_window_seconds
    if not (
        await ratelimit.hit(redis, f"forgot:ip:{client_ip(request)}", 10, window)
        and await ratelimit.hit(redis, f"forgot:email:{body.email}", 3, window)
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")
    user = await db.scalar(select(User).where(User.email == body.email))
    if user is not None and user.is_active:
        token = await issue_token(db, user, RESET)
        audit(
            db,
            "user.password_reset_requested",
            actor_id=user.id,
            subject=user.email,
            ip=client_ip(request),
        )
        await db.commit()
        await enqueue(
            "send_email",
            user.email,
            "Reset your SecAI password",
            [
                "Someone asked to reset the password for this SecAI account.",
                "Use the link below within 30 minutes to choose a new password. "
                "If two-factor authentication is on, you'll still need your authenticator app "
                "to sign in.",
                "If you didn't ask for this, ignore this email: your password stays the same.",
            ],
            (
                "Choose a new password",
                f"{settings.web_origin.rstrip('/')}/reset-password?token={token}",
            ),
        )
    # Same answer either way, so this can't be used to find out who has an account.
    return {"status": "sent_if_account_exists"}


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    body: ResetPasswordIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    if len(body.password) < settings.password_min_length:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Use at least {settings.password_min_length} characters",
        )
    user = await consume_token(db, body.token, RESET)
    user.password_hash = hash_password(body.password)
    # Resetting proves control of the mailbox, so it also confirms the address.
    user.email_verified_at = user.email_verified_at or datetime.now(UTC)
    await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    audit(db, "user.password_reset", actor_id=user.id, subject=user.email, ip=client_ip(request))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/change", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordIn,
    request: Request,
    ctx: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> Response:
    user = ctx.user
    if not await ratelimit.hit(
        redis, f"change-password:{user.id}", 5, settings.login_rate_limit_window_seconds
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")
    if not verify_password(user.password_hash, body.current_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is incorrect")
    if len(body.new_password) < settings.password_min_length:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Use at least {settings.password_min_length} characters",
        )
    user.password_hash = hash_password(body.new_password)
    # Sign out everywhere else; this session stays.
    await db.execute(
        delete(UserSession).where(UserSession.user_id == user.id, UserSession.id != ctx.session.id)
    )
    audit(db, "user.password_changed", actor_id=user.id, subject=user.email, ip=client_ip(request))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
