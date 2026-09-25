import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.org import get_current_org
from app.db.session import get_db
from app.models import Finding, Organization, Scan, Target
from app.scanning.normalize import SEVERITY_ORDER
from app.schemas.targets import FindingOut, ScanOut

router = APIRouter(prefix="/scans", tags=["scans"])


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: uuid.UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ScanOut:
    scan = await db.scalar(select(Scan).where(Scan.id == scan_id, Scan.org_id == org.id))
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    findings = (await db.scalars(select(Finding).where(Finding.scan_id == scan.id))).all()
    target = await db.get(Target, scan.target_id) if scan.target_id else None
    out = ScanOut.model_validate(scan)
    out.target_url = target.url if target else None
    out.findings = sorted(
        (FindingOut.model_validate(f) for f in findings),
        key=lambda f: (SEVERITY_ORDER[f.severity], f.title),
    )
    return out
