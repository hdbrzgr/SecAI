from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, client_ip, get_auth, get_pending_auth, get_redis
from app.core import ratelimit
from app.core.config import Settings, get_settings
from app.core.instance import audit, get_instance_settings
from app.core.mail import smtp_configured
from app.core.security import (
    decrypt_secret,
    encrypt_secret,
    hash_password,
    hash_token,
    new_session_token,
    new_totp_secret,
    password_needs_rehash,
    totp_uri,
    verify_password,
    verify_totp,
)
from app.db.session import get_db
from app.models import Membership, Organization, OrgRole, User, UserSession
from app.scanning.queue import Enqueue, get_enqueue
from app.schemas.auth import (
    LoginIn,
    LoginOut,
    MfaDisableIn,
    MfaSetupOut,
    RegisterIn,
    TotpCodeIn,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS = "Invalid email or password"


async def _start_session(
    db: AsyncSession,
    response: Response,
    request: Request,
    settings: Settings,
    user: User,
    *,
    mfa_verified: bool,
) -> None:
    token = new_session_token()
    now = datetime.now(UTC)
    lifetime = (
        timedelta(hours=settings.session_max_age_hours)
        if mfa_verified
        else timedelta(minutes=settings.mfa_pending_minutes)
    )
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            mfa_verified=mfa_verified,
            expires_at=now + lifetime,
            ip=client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:512],
        )
    )
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    enqueue: Enqueue = Depends(get_enqueue),
) -> User:
    if not await ratelimit.hit(
        redis, f"register:ip:{client_ip(request)}", 10, settings.login_rate_limit_window_seconds
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")

    is_first_user = (await db.scalar(select(func.count()).select_from(User))) == 0
    instance = await get_instance_settings(db, settings)
    # The first account can always be created so a fresh instance gets its admin.
    if not instance.registration_open and not is_first_user:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Registration is disabled")
    if len(body.password) < settings.password_min_length:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Password must be at least {settings.password_min_length} characters",
        )

    user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        is_superuser=is_first_user,
    )
    org = Organization(name=f"{body.name or body.email.split('@')[0]}'s workspace")
    db.add_all([user, org])
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        # Deliberately vague to avoid confirming which emails have accounts.
        raise HTTPException(status.HTTP_409_CONFLICT, "Could not create account") from None
    db.add(Membership(org_id=org.id, user_id=user.id, role=OrgRole.owner))
    audit(
        db,
        "user.registered",
        actor_id=user.id,
        org_id=org.id,
        subject=user.email,
        ip=client_ip(request),
    )
    await _start_session(db, response, request, settings, user, mfa_verified=True)
    if smtp_configured() and not user.is_superuser:
        from app.api.routes.account import send_verification

        await send_verification(db, user, settings, enqueue)
    await db.commit()
    return user


@router.post("/login", response_model=LoginOut)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> LoginOut:
    window = settings.login_rate_limit_window_seconds
    ip_ok = await ratelimit.hit(
        redis, f"login:ip:{client_ip(request)}", settings.login_rate_limit_per_ip, window
    )
    email_ok = await ratelimit.hit(
        redis, f"login:email:{body.email}", settings.login_rate_limit_per_email, window
    )
    if not (ip_ok and email_ok):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")

    user = await db.scalar(select(User).where(User.email == body.email))
    # verify_password runs a real hash comparison even when the user is missing.
    if not verify_password(user.password_hash if user else None, body.password) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    await ratelimit.reset(redis, f"login:email:{body.email}")

    await _start_session(db, response, request, settings, user, mfa_verified=not user.mfa_enabled)
    await db.commit()
    if user.mfa_enabled:
        return LoginOut(mfa_required=True)
    return LoginOut(mfa_required=False, user=UserOut.model_validate(user))


@router.post("/login/mfa", response_model=LoginOut)
async def login_mfa(
    body: TotpCodeIn,
    request: Request,
    response: Response,
    ctx: AuthContext = Depends(get_pending_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> LoginOut:
    user = ctx.user
    if ctx.session.mfa_verified:
        return LoginOut(mfa_required=False, user=UserOut.model_validate(user))
    if not await ratelimit.hit(
        redis, f"mfa:user:{user.id}", 5, settings.login_rate_limit_window_seconds
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")

    secret = decrypt_secret(user.totp_secret_enc) if user.totp_secret_enc else None
    counter = verify_totp(secret, body.code, user.totp_last_counter) if secret else None
    if counter is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid code")
    user.totp_last_counter = counter
    await ratelimit.reset(redis, f"mfa:user:{user.id}")

    # Issue a fresh token for the fully authenticated session (prevents session fixation).
    await db.delete(ctx.session)
    await _start_session(db, response, request, settings, user, mfa_verified=True)
    await db.commit()
    return LoginOut(mfa_required=False, user=UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    ctx: AuthContext = Depends(get_pending_auth),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    await db.delete(ctx.session)
    await db.commit()
    _clear_cookie(response, settings)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    response: Response,
    ctx: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    await db.execute(delete(UserSession).where(UserSession.user_id == ctx.user.id))
    await db.commit()
    _clear_cookie(response, settings)


@router.get("/me", response_model=UserOut)
async def me(ctx: AuthContext = Depends(get_auth)) -> User:
    return ctx.user


@router.post("/mfa/setup", response_model=MfaSetupOut)
async def mfa_setup(
    ctx: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> MfaSetupOut:
    user = ctx.user
    if user.mfa_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Two-factor authentication is already on")
    secret = new_totp_secret()
    user.totp_pending_secret_enc = encrypt_secret(secret)
    await db.commit()
    return MfaSetupOut(secret=secret, otpauth_uri=totp_uri(secret, user.email))


@router.post("/mfa/enable", response_model=UserOut)
async def mfa_enable(
    body: TotpCodeIn,
    ctx: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> User:
    user = ctx.user
    if not user.totp_pending_secret_enc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Start setup first")
    if not await ratelimit.hit(
        redis, f"mfa:user:{user.id}", 5, settings.login_rate_limit_window_seconds
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")
    secret = decrypt_secret(user.totp_pending_secret_enc)
    counter = verify_totp(secret, body.code, None) if secret else None
    if counter is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code")
    user.totp_secret_enc = user.totp_pending_secret_enc
    user.totp_pending_secret_enc = None
    user.totp_last_counter = counter
    user.mfa_enabled = True
    # Sign out every other session so they must pass the new second factor.
    await db.execute(
        delete(UserSession).where(UserSession.user_id == user.id, UserSession.id != ctx.session.id)
    )
    await db.commit()
    return user


@router.post("/mfa/disable", response_model=UserOut)
async def mfa_disable(
    body: MfaDisableIn,
    ctx: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> User:
    user = ctx.user
    if not user.mfa_enabled or not user.totp_secret_enc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Two-factor authentication is off")
    if not await ratelimit.hit(
        redis, f"mfa:user:{user.id}", 5, settings.login_rate_limit_window_seconds
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")
    secret = decrypt_secret(user.totp_secret_enc)
    counter = verify_totp(secret, body.code, user.totp_last_counter) if secret else None
    if not verify_password(user.password_hash, body.password) or counter is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid password or code")
    user.mfa_enabled = False
    user.totp_secret_enc = None
    user.totp_last_counter = None
    await db.commit()
    return user
