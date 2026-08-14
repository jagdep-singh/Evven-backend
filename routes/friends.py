from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.groups import GroupStatus
from models.user import User
from schemas.common import SuccessResponse
from schemas.friend import (
    FriendDetailResponse,
    FriendRequestCreate,
    FriendRequestListResponse,
    FriendResponse,
)
from services.friend_service import (
    accept_friend_request,
    get_friend_detail,
    list_friend_requests,
    list_friends,
    reject_friend_request,
    send_friend_request,
    unfriend,
)

router = APIRouter(prefix="/friends", tags=["Friends"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_friend_request(
    friend_data: FriendRequestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await send_friend_request(user.id, friend_data.user_code, db)

    status_msg = (
        "Friend request sent"
        if group.status == GroupStatus.PENDING
        else "Friend added successfully"
    )

    return SuccessResponse(
        message=status_msg, data={"group_id": group.id, "status": group.status.value}
    )


@router.get("/requests", response_model=SuccessResponse[FriendRequestListResponse])
async def get_friends_request(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    data = await list_friend_requests(user.id, db)
    return SuccessResponse(message="Friend requests fetched", data=data)


@router.post("/{group_id}/accept")
async def accept_request(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await accept_friend_request(group_id, user.id, db)
    return SuccessResponse(
        message="Friend request accepted",
        data={"group_id": group.id},
    )


@router.delete("/{group_id}/reject")
async def reject_request(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await reject_friend_request(group_id, user.id, db)
    return SuccessResponse(message="Friend request rejected/cancelled", data=None)


@router.get("/", response_model=SuccessResponse[list[FriendResponse]])
async def get_friends(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await list_friends(user.id, db)
    return SuccessResponse(message="Friends list fetched", data=data)


@router.get("/{group_id}", response_model=SuccessResponse[FriendDetailResponse])
async def get_friend(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await get_friend_detail(group_id, user.id, db)
    return SuccessResponse(message="Friend detail fetched", data=data)


@router.delete("/{group_id}")
async def remove_friend(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await unfriend(group_id, user.id, db)
    return SuccessResponse(message="Friend removed successfully", data=None)
