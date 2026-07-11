from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.groups import Group
from repository.expense_repository import ExpenseRepository
from repository.group_member_repository import GroupMemberRepository
from repository.group_repository import GroupRepository
from repository.user_repository import UserRepository
from schemas.common import SuccessResponse
from schemas.groups import GroupCreate, GroupMemberResponse, GroupResponse, GroupUpdate


# private member
async def _can_access_group(
    group: Group, user_id: UUID, member_repo: GroupMemberRepository
) -> bool:
    return group.created_by == user_id or await member_repo.is_member(user_id, group.id)


def _member_response_data(member) -> dict:
    return {
        "id": member.id,
        "name": member.user.name if member.user else str(member.user_id)[:8],
        "user_code": member.user.user_code if member.user else "",
        "group_id": member.group_id,
        "user_id": member.user_id,
        "joined_at": member.joined_at,
    }
    # just adding to get the frontend working we can remove it late


async def create_group(
    group_data: GroupCreate, db: AsyncSession, user_id: UUID
) -> SuccessResponse[GroupResponse]:
    repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)
    group = Group(name=group_data.name, created_by=user_id)
    created_group = await repo.create(group)
    await member_repo.add_group_member(user_id, created_group.id)
    return SuccessResponse(
        message="Group created successfully",
        data=GroupResponse.model_validate(created_group),
    )


async def list_groups(
    db: AsyncSession, user_id: UUID
) -> SuccessResponse[list[GroupResponse]]:
    repo = GroupRepository(db)

    groups = await repo.get_user_groups(user_id)

    if not groups:
        raise SuccessResponse(message="No groups found", data=[])

    return SuccessResponse(
        message="Group fetched successfully",
        data=[GroupResponse.model_validate(g) for g in groups],
    )


async def get_group(
    db: AsyncSession, group_id: UUID, user_id: UUID
) -> SuccessResponse[GroupResponse]:
    repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if not await _can_access_group(group, user_id, member_repo):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    return SuccessResponse(
        message="Group found", data=GroupResponse.model_validate(group)
    )


async def update_group(
    db: AsyncSession, group_id: UUID, group_data: GroupUpdate, user_id: UUID
) -> SuccessResponse[GroupResponse]:
    repo = GroupRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user_id:
        raise HTTPException(
            status_code=403, detail="Only group creator can update the group"
        )

    updated_group = await repo.update(group, group_data.model_dump(exclude_unset=True))

    return SuccessResponse(
        message="Group updated successfully",
        data=GroupResponse.model_validate(updated_group),
    )


async def delete_group(
    group_id: UUID, user_id: UUID, db: AsyncSession
) -> SuccessResponse[None]:
    repo = GroupRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user_id:
        raise HTTPException(
            status_code=403, detail="Only group creator can delete the group"
        )

    await repo.delete(group)

    return SuccessResponse(message="Group deleted successfully", data=None)


async def add_member(
    group_id: UUID, user_code: str, db: AsyncSession, current_user_id: UUID
) -> SuccessResponse[GroupMemberResponse]:
    repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)
    user_repo = UserRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    user = await user_repo.get_user_by_user_code(user_code)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.id

    if not await _can_access_group(group, current_user_id, member_repo):
        raise HTTPException(status_code=403, detail="Member is not authorized")

    existing_user = await member_repo.get_group_member(user_id, group_id)
    if existing_user:
        raise HTTPException(
            status_code=400, detail="User is already existing in the group"
        )

    await member_repo.add_group_member(user_id, group_id)
    member = await member_repo.get_group_member(user_id, group_id)
    if not member:
        raise HTTPException(status_code=500, detail="Member could not be loaded")

    return SuccessResponse(
        message="Member added successfully",
        data=GroupMemberResponse.model_validate(_member_response_data(member)),
    )


async def remove_member(
    group_id: UUID, user_id: UUID, db: AsyncSession, current_user_id: UUID
) -> SuccessResponse[None]:
    repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)
    expense_repo = ExpenseRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if not await _can_access_group(group, current_user_id, member_repo):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    member = await member_repo.get_group_member(user_id, group_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if await expense_repo.has_pending_balance(group_id, user_id):
        raise HTTPException(
            status_code=400, detail="User has a pending balance and cannot be removed"
        )
    # Adding function from balance_repository.py

    await member_repo.remove_group_member(member)

    return SuccessResponse(message="Member deleted successfully", data=None)


async def list_members(
    group_id: UUID, db: AsyncSession, current_user_id: UUID
) -> SuccessResponse[list[GroupMemberResponse]]:
    repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if not await _can_access_group(group, current_user_id, member_repo):
        raise HTTPException(status_code=403, detail="Member is not authorised")

    members = await member_repo.list_group_members(group_id)

    return SuccessResponse(
        message="List of members fetched successfully",
        data=[
            GroupMemberResponse.model_validate(_member_response_data(m))
            for m in members
        ],
    )
