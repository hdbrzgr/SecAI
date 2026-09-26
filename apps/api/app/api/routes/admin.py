"""Instance administration. Every route requires an instance admin (superuser) session."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user
from app.core.config import Settings, get_settings
from app.core.instance import audit, get_instance_settings
from app.db.session import get_db
from app.models import (
    AuditEvent,
    BlockedDomain,
    Membership,
    Organization,
    Scan,
    ScanStatus,
    Target,
    User,
    UserSession,
)
from app.scanning.targets import InvalidTarget, normalize_url
from app.schemas.admin import (
    AdminUser,
    AdminUserPatch,
    AuditEventOut,
    BlockedDomainIn,
    BlockedDomainOut,
    InstanceSettingsOut,
    InstanceSettingsPatch,
    Overview,
)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only instance admins can do this")
    return user


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


async def _count(db: AsyncSession, stmt) -> int:
    return int(await db.scalar(stmt) or 0)


@router.get("/overview", response_model=Overview)
async def overview(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> Overview:
    now = datetime.now(UTC)
    instance = await get_instance_settings(db, settings)
    recent = (
        await db.scalars(select(Scan.summary).where(Scan.created_at >= now - timedelta(days=30)))
    ).all()
    tokens = 0
    for summary in recent:
        usage = ((summary or {}).get("ai") or {}).get("usage") or {}
        tokens += int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
    await db.commit()  # persists the settings row if this was its first read
    return Overview(
        users=await _count(db, select(func.count()).select_from(User)),
        active_users=await _count(db, select(func.count()).select_from(User).where(User.is_active)),
        workspaces=await _count(db, select(func.count()).select_from(Organization)),
        websites=await _count(db, select(func.count()).select_from(Target)),
        verified_websites=await _count(
            db, select(func.count()).select_from(Target).where(Target.verified_at.is_not(None))
        ),
        scans_total=await _count(db, select(func.count()).select_from(Scan)),
        scans_last_24h=await _count(
            db,
            select(func.count())
            .select_from(Scan)
            .where(Scan.created_at >= now - timedelta(days=1)),
        ),
        scans_running=await _count(
            db,
            select(func.count())
            .select_from(Scan)
            .where(Scan.status.in_((ScanStatus.queued, ScanStatus.running))),
        ),
        ai_tokens_last_30d=tokens,
        scanning_paused=instance.scanning_paused,
        smtp_configured=bool(settings.smtp_host),
        ai_configured=bool(settings.ai_api_key),
        zap_configured=bool(settings.zap_url and settings.zap_api_key),
    )


@router.get("/users", response_model=list[AdminUser])
async def list_users(q: str | None = None, db: AsyncSession = Depends(get_db)) -> list[AdminUser]:
    websites = (
        select(Membership.user_id, func.count(Target.id).label("n"))
        .join(Target, Target.org_id == Membership.org_id)
        .group_by(Membership.user_id)
        .subquery()
    )
    scans = (
        select(Scan.created_by_id, func.count(Scan.id).label("n"))
        .group_by(Scan.created_by_id)
        .subquery()
    )
    stmt = (
        select(User, func.coalesce(websites.c.n, 0), func.coalesce(scans.c.n, 0))
        .outerjoin(websites, websites.c.user_id == User.id)
        .outerjoin(scans, scans.c.created_by_id == User.id)
        .order_by(User.created_at.desc())
        .limit(500)
    )
    if q:
        stmt = stmt.where(User.email.ilike(f"%{q.strip().lower()}%"))
    rows = (await db.execute(stmt)).all()
    return [
        AdminUser(
            id=u.id,
            email=u.email,
            name=u.name,
            is_active=u.is_active,
            is_superuser=u.is_superuser,
            mfa_enabled=u.mfa_enabled,
            email_verified=u.email_verified_at is not None,
            created_at=u.created_at,
            websites=w,
            scans=n,
        )
        for u, w, n in rows
    ]


@router.patch("/users/{user_id}", response_model=AdminUser)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserPatch,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id and (body.is_active is False or body.is_superuser is False):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You can't deactivate yourself or remove your own admin role"
        )
    changes = body.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(user, field, value)
    if body.is_active is False:
        await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    audit(
        db,
        "admin.user.updated",
        actor_id=admin.id,
        subject=user.email,
        ip=client_ip(request),
        **changes,
    )
    await db.commit()
    rows = await list_users(q=user.email, db=db)
    return next(r for r in rows if r.id == user.id)


@router.get("/settings", response_model=InstanceSettingsOut)
async def read_settings(
    db: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> InstanceSettingsOut:
    row = await get_instance_settings(db, settings)
    await db.commit()
    return InstanceSettingsOut.model_validate(row)


@router.patch("/settings", response_model=InstanceSettingsOut)
async def update_settings(
    body: InstanceSettingsPatch,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> InstanceSettingsOut:
    row = await get_instance_settings(db, settings)
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(row, field, value)
    if changes.get("scanning_paused") is False:
        row.scanning_paused_reason = None
    row.updated_by_id = admin.id
    audit(db, "admin.settings.updated", actor_id=admin.id, ip=client_ip(request), **changes)
    await db.commit()
    return InstanceSettingsOut.model_validate(row)


@router.get("/blocked-domains", response_model=list[BlockedDomainOut])
async def list_blocked(db: AsyncSession = Depends(get_db)) -> list[BlockedDomain]:
    return list((await db.scalars(select(BlockedDomain).order_by(BlockedDomain.domain))).all())


@router.post(
    "/blocked-domains", response_model=BlockedDomainOut, status_code=status.HTTP_201_CREATED
)
async def add_blocked(
    body: BlockedDomainIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> BlockedDomain:
    try:
        _, hostname = normalize_url(body.domain)
    except InvalidTarget as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    entry = BlockedDomain(domain=hostname, reason=body.reason, created_by_id=admin.id)
    db.add(entry)
    audit(
        db,
        "admin.domain.blocked",
        actor_id=admin.id,
        subject=hostname,
        ip=client_ip(request),
        reason=body.reason,
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"{hostname} is already blocked") from None
    return entry


@router.delete("/blocked-domains/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_blocked(
    entry_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    entry = await db.get(BlockedDomain, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    audit(
        db, "admin.domain.unblocked", actor_id=admin.id, subject=entry.domain, ip=client_ip(request)
    )
    await db.delete(entry)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit", response_model=list[AuditEventOut])
async def audit_log(
    action: str | None = None, limit: int = 200, db: AsyncSession = Depends(get_db)
) -> list[AuditEventOut]:
    stmt = (
        select(AuditEvent, User.email)
        .outerjoin(User, User.id == AuditEvent.actor_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(min(max(limit, 1), 1000))
    )
    if action:
        stmt = stmt.where(AuditEvent.action.startswith(action))
    out = []
    for event, email in (await db.execute(stmt)).all():
        item = AuditEventOut.model_validate(event)
        item.actor_email = email
        out.append(item)
    return out
