from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Membership, Organization, User


async def get_current_org(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Organization:
    """The user's workspace. Every user has exactly one for now (created at sign-up)."""
    org = await db.scalar(
        select(Organization)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Membership.user_id == user.id)
        .order_by(Membership.created_at)
        .limit(1)
    )
    if org is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No workspace")
    return org
