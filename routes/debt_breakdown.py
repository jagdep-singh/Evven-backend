from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.user import User
from services.debt_breakdown_service import (
    get_user_debt_breakdown,
)

router = APIRouter(prefix="/groups", tags=["Debt Breakdown"])


@router.get("/{group_id}/debt-breakdown")
async def get_group_debt_breakdown(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_user_debt_breakdown(group_id, user.id, db)
