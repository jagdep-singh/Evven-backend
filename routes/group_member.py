from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.groups import AddMember, GroupMemberResponse
from services.group_service import add_member, list_members, remove_member

router = APIRouter(prefix="/groups", tags=["Group Members"])


@router.get("/{group_id}/members")
async def list_member(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return await list_members(group_id, db, current_user.id)


@router.post("/{group_id}/members", response_model=GroupMemberResponse)
async def add_member_by_id(
    group_id: UUID,
    member: AddMember,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return await add_member(group_id, member.user_code, db, current_user.id)


@router.delete("/{group_id}/members/{user_id}")
async def remove_member_by_id(
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return await remove_member(group_id, user_id, db, current_user.id)
