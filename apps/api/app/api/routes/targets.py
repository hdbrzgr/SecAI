import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, get_redis
from app.api.org import get_current_org
from app.core import ratelimit
from app.core.config import Settings, get_settings
from app.core.netguard import TargetNotAllowed, resolve
from app.db.session import get_db
from app.models import Organization, Scan, ScanKind, ScanStatus, Target, User
from app.scanning.queue import Enqueue, get_enqueue
from app.scanning.targets import (
    InvalidTarget,
    check_ownership,
    new_verification_token,
    normalize_url,
)
from app.schemas.targets import ScanBrief, ScanIn, ScanOut, TargetIn, TargetOut, VerifyIn

router = APIRouter(prefix="/targets", tags=["targets"])

ACTIVE = (ScanStatus.queued, ScanStatus.running)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _verification_expired(target: Target, settings: Settings) -> bool:
    if target.verified_at is None:
        return False
    return datetime.now(UTC) - _aware(target.verified_at) > timedelta(
        days=settings.verification_max_age_days
    )


async def _last_scan(db: AsyncSession, target_id: uuid.UUID) -> Scan | None:
    return await db.scalar(
        select(Scan).where(Scan.target_id == target_id).order_by(Scan.created_at.desc()).limit(1)
    )


async def _out(db: AsyncSession, target: Target, settings: Settings) -> TargetOut:
    out = TargetOut.model_validate(target)
    out.verification_expired = _verification_expired(target, settings)
    last = await _last_scan(db, target.id)
    out.last_scan = ScanBrief.model_validate(last) if last else None
    return out


async def _get_target(db: AsyncSession, org: Organization, target_id: uuid.UUID) -> Target:
    target = await db.scalar(select(Target).where(Target.id == target_id, Target.org_id == org.id))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Website not found")
    return target


@router.get("", response_model=list[TargetOut])
async def list_targets(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[TargetOut]:
    targets = (
        await db.scalars(select(Target).where(Target.org_id == org.id).order_by(Target.created_at))
    ).all()
    return [await _out(db, t, settings) for t in targets]


@router.post("", response_model=TargetOut, status_code=status.HTTP_201_CREATED)
async def add_target(
    body: TargetIn,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TargetOut:
    try:
        url, hostname = normalize_url(body.url)
    except InvalidTarget as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    try:
        await resolve(hostname, 443)
    except TargetNotAllowed as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"SecAI can't scan this address: {exc}. Only public websites can be scanned.",
        ) from None

    target = Target(
        org_id=org.id, url=url, hostname=hostname, verification_token=new_verification_token()
    )
    db.add(target)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"{hostname} is already in your websites"
        ) from None
    return await _out(db, target, settings)


@router.get("/{target_id}", response_model=TargetOut)
async def get_target(
    target_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TargetOut:
    return await _out(db, await _get_target(db, org, target_id), settings)


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Response:
    target = await _get_target(db, org, target_id)
    await db.delete(target)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{target_id}/verify", response_model=TargetOut)
async def verify_target(
    target_id: uuid.UUID,
    body: VerifyIn,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> TargetOut:
    target = await _get_target(db, org, target_id)
    # Each check makes outbound requests, so keep it from being used as a request cannon.
    if not await ratelimit.hit(redis, f"verify:target:{target.id}", 20, 60 * 60):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many checks, try again later")
    now = datetime.now(UTC)
    target.last_verification_check_at = now
    ok = await check_ownership(target.url, target.hostname, body.method, target.verification_token)
    if ok:
        target.verified_at = now
        target.verification_method = body.method
    await db.commit()
    if not ok:
        what = {
            "dns_txt": f"the TXT record on {target.hostname}",
            "well_known_file": "the verification file",
            "meta_tag": "the meta tag on your home page",
        }[body.method.value]
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"SecAI couldn't find {what} yet. Changes can take a few minutes to show up; "
            "try again shortly.",
        )
    return await _out(db, target, settings)


@router.get("/{target_id}/scans", response_model=list[ScanBrief])
async def list_scans(
    target_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[Scan]:
    target = await _get_target(db, org, target_id)
    return list(
        (
            await db.scalars(
                select(Scan)
                .where(Scan.target_id == target.id)
                .order_by(Scan.created_at.desc())
                .limit(50)
            )
        ).all()
    )


@router.post("/{target_id}/scans", response_model=ScanOut, status_code=status.HTTP_202_ACCEPTED)
async def start_scan(
    target_id: uuid.UUID,
    body: ScanIn,
    request: Request,
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    enqueue: Enqueue = Depends(get_enqueue),
) -> ScanOut:
    target = await _get_target(db, org, target_id)
    if not body.authorized:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Confirm that you own this website or have written permission to test it",
        )
    if target.verified_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Verify that you own this website first")
    if _verification_expired(target, settings):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ownership proof has expired. Verify the website again"
        )
    active = await db.scalar(
        select(func.count())
        .select_from(Scan)
        .where(Scan.target_id == target.id, Scan.status.in_(ACTIVE))
    )
    if active:
        raise HTTPException(status.HTTP_409_CONFLICT, "A scan of this website is already running")
    since = datetime.now(UTC) - timedelta(days=1)
    today = await db.scalar(
        select(func.count())
        .select_from(Scan)
        .where(Scan.org_id == org.id, Scan.created_at >= since)
    )
    if (today or 0) >= settings.scans_per_day_per_org:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Your workspace has used its {settings.scans_per_day_per_org} scans "
            "for the last 24 hours",
        )

    now = datetime.now(UTC)
    scan = Scan(
        org_id=org.id,
        target_id=target.id,
        created_by_id=user.id,
        kind=ScanKind.dast,
        status=ScanStatus.queued,
        current_step="Waiting for a worker",
        attested_at=now,
        attested_ip=client_ip(request),
    )
    db.add(scan)
    await db.commit()
    await enqueue("run_scan", str(scan.id))
    out = ScanOut.model_validate(scan)
    out.target_url = target.url
    return out
