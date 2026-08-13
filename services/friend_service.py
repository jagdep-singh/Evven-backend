from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.groups import Group, GroupStatus, GroupType
from repository.expense_repository import ExpenseRepository
from repository.friend_repository import FriendRepository
from repository.group_member_repository import GroupMemberRepository
from repository.group_repository import GroupRepository
from repository.settlement_repository import SettlementRepository
from repository.user_repository import UserRepository
from schemas.friend import (
    FriendActivityEntry,
    FriendDetailResponse,
    FriendRequestListResponse,
    FriendResponse,
    PendingRequestResponse,
)
from services.balance_service import BalanceService


async def send_friend_request(
    current_user_id: UUID, target_user_code: str, db: AsyncSession
) -> Group:
    user_repo = UserRepository(db)
    friend_repo = FriendRepository(db)

    target_user = await user_repo.get_user_by_user_code(target_user_code)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == current_user_id:
        raise HTTPException(
            status_code=400, detail="You cannot add yourself as a friend"
        )

    existing_group = await friend_repo.find_friend_group_between_users(
        current_user_id, target_user.id
    )
    if existing_group:
        if existing_group.status == GroupStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Already friends")
        if existing_group.status == GroupStatus.PENDING:
            if existing_group.created_by == current_user_id:
                raise HTTPException(
                    status_code=400, detail="Friend request already pending"
                )
            else:
                return await accept_friend_request(
                    existing_group.id, current_user_id, db
                )
        if existing_group.status == GroupStatus.REMOVED:
            updated_group = await friend_repo.update_status(
                existing_group, GroupStatus.ACTIVE
            )
            return updated_group

    new_group = await friend_repo.create_pending_friend_group(
        requester_id=current_user_id, recipient_id=target_user.id
    )

    return new_group


async def list_friend_requests(
    current_user_id: UUID, db: AsyncSession
) -> FriendRequestListResponse:
    friend_repo = FriendRepository(db)

    pending_groups = await friend_repo.list_friend_groups_by_user_and_status(
        user_id=current_user_id, statuses=[GroupStatus.PENDING]
    )

    incoming = []
    outgoing = []

    for group in pending_groups:
        members = await GroupMemberRepository(db).list_group_members(group.id)
        other_member = next((m for m in members if m.user_id != current_user_id), None)
        if not other_member:
            continue

        is_outgoing = group.created_by == current_user_id
        direction = "outgoing" if is_outgoing else "incoming"

        request_data = PendingRequestResponse(
            id=group.id,
            user_id=other_member.id,
            name=other_member.name,
            user_code=other_member.user.user_code,
            profile_picture=other_member.user.profile_picture,
            created_at=group.created_at,
            direction=direction,
        )

        if is_outgoing:
            outgoing.append(request_data)
        else:
            incoming.append(request_data)

    return FriendRequestListResponse(incoming=incoming, outgoing=outgoing)


async def accept_friend_request(
    friend_group_id: UUID, current_user_id: UUID, db: AsyncSession
) -> Group:
    friend_repo = FriendRepository(db)
    group_repo = GroupRepository(db)

    group = await group_repo.get_by_id(friend_group_id)
    if not group or group.group_type != GroupType.FRIEND:
        raise HTTPException(status_code=404, detail="Friend group not found")

    if group.status != GroupStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request is not pending")

    if group.created_by == current_user_id:
        raise HTTPException(status_code=403, detail="Cannot accept your own request")

    member_repo = GroupMemberRepository(db)
    if not await member_repo.is_member(current_user_id, group.id):
        raise HTTPException(
            status_code=403, detail="You are not a member of this group"
        )

    updated_group = await friend_repo.update_status(group, GroupStatus.ACTIVE)
    return updated_group


async def reject_friend_request(
    friend_group_id: UUID, current_user_id: UUID, db: AsyncSession
) -> None:
    friend_repo = FriendRepository(db)
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    group = await group_repo.get_by_id(friend_group_id)
    if not group or group.group_type != GroupType.FRIEND:
        raise HTTPException(status_code=404, detail="Friend group not found")

    if group.status != GroupStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request is not pending")

    if not await member_repo.is_member(current_user_id, group.id):
        raise HTTPException(
            status_code=403, detail="You are not a member of this group"
        )

    await friend_repo.hard_delete_pending_group(group)


async def list_friends(current_user_id: UUID, db: AsyncSession) -> list[FriendResponse]:
    friend_repo = FriendRepository(db)
    balance_service = BalanceService(db)

    groups = await friend_repo.list_friend_groups_by_user_and_status(
        user_id=current_user_id, statuses=[GroupStatus.ACTIVE]
    )

    result = []
    group_ids = [g.id for g in groups]
    last_activity = await friend_repo.get_last_activity_by_group_ids(group_ids)

    for group in groups:
        members = await GroupMemberRepository(db).list_group_members(group.id)
        other = next((m for m in members if m.user_id != current_user_id), None)
        if not other:
            continue

        balances = await balance_service.get_user_balance_in_group(
            user_id=current_user_id, group_id=group.id
        )

        balance = balances.get(other.user_id, Decimal("0"))

        result.append(
            FriendResponse(
                id=other.user_id,
                name=other.user.name,
                user_code=other.user.user_code,
                profile_picture=other.user.profile_picture,
                group_id=group.id,
                balance=balance,
            ),
            last_activity.get(group.id),
        )

    result.sort(
        key=lambda pair: (
            pair[1] is None,
            -(pair[1].timestamp()) if pair[1] else 0,
            pair[0].name.lower(),
        )
    )

    return [friend for friend, _ in result]


async def get_friend_detail(
    friend_group_id: UUID,
    current_user_id: UUID,
    db: AsyncSession,
) -> FriendDetailResponse:
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)
    balance_service = BalanceService(db)

    group = await group_repo.get_by_id(friend_group_id)
    if not group or group.group_type != GroupType.FRIEND:
        raise HTTPException(status_code=404, detail="Friend group not found")

    if group.status != GroupStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Friend relationship is not active")

    if not await member_repo.is_member(current_user_id, group.id):
        raise HTTPException(
            status_code=403, detail="You are not a member of this group"
        )

    members = await member_repo.list_group_members(group.id)
    other = next((m for m in members if m.user_id != current_user_id), None)
    if not other:
        raise HTTPException(
            status_code=500, detail="Group has only one member? This should not happen"
        )

    balances = await balance_service.get_user_balance_in_group(
        user_id=current_user_id,
        group_id=group.id,
    )
    balance = balances.get(other.user_id, Decimal("0"))

    activity = await _build_friend_activity(group.id, current_user_id, db)

    return FriendDetailResponse(
        id=other.user_id,
        name=other.user.name,
        user_code=other.user.user_code,
        profile_picture=other.user.profile_picture,
        group_id=group.id,
        balance=balance,
        activity=activity,
    )


async def unfriend(
    friend_group_id: UUID,
    current_user_id: UUID,
    db: AsyncSession,
) -> None:
    group_repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)
    expense_repo = ExpenseRepository(db)
    friend_repo = FriendRepository(db)

    group = await group_repo.get_by_id(friend_group_id)
    if not group or group.group_type != GroupType.FRIEND:
        raise HTTPException(status_code=404, detail="Friend group not found")

    if group.status != GroupStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Friend relationship is not active")

    if not await member_repo.is_member(current_user_id, group.id):
        raise HTTPException(
            status_code=403, detail="You are not a member of this group"
        )

    if await expense_repo.has_pending_balance(group.id, current_user_id):
        raise HTTPException(
            status_code=400,
            detail="You have an outstanding balance with this friend. Settle up before unfriending.",
        )

    # Soft-remove: set status to REMOVED
    await friend_repo.update_status(group, GroupStatus.REMOVED)


async def _build_friend_activity(
    group_id: UUID,
    current_user_id: UUID,
    db: AsyncSession,
) -> list[FriendActivityEntry]:
    expense_repo = ExpenseRepository(db)
    settlement_repo = SettlementRepository(db)

    expenses = await expense_repo.get_group_expense_with_splits(group_id)
    settlements = await settlement_repo.get_settlements_by_group_id(group_id)

    activity: list[FriendActivityEntry] = []

    for expense in expenses:
        your_split = next(
            (s.amount for s in expense.splits if s.user_id == current_user_id),
            None,
        )
        activity.append(
            FriendActivityEntry(
                type="expense",
                id=expense.id,
                title=expense.title,
                amount=expense.amount,
                created_at=expense.created_at,
                your_share=your_split,
            )
        )

    for settlement in settlements:
        direction = (
            "You paid" if settlement.payer_id == current_user_id else "You received"
        )
        activity.append(
            FriendActivityEntry(
                type="settlement",
                id=settlement.id,
                title=direction,
                amount=settlement.amount,
                created_at=settlement.created_at,
            )
        )

    activity.sort(key=lambda entry: entry.created_at, reverse=True)
    return activity
