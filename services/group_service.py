from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.groups import Group
from repos.group_member_repository import GroupMemberRepository
from repos.group_repository import GroupRepository
from schemas.groups import GroupCreate, GroupMemberResponse, GroupResponse, GroupUpdate


async def create_group(
    group_data: GroupCreate, db: AsyncSession, user_id: UUID
) -> dict:

    repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    group = Group(name=group_data.name, created_by=user_id)

    created_group = await repo.create(group)

    await member_repo.add(created_group.id, user_id)

    return {
        "message": "Group created successfully",
        "group": GroupResponse.model_validate(created_group),
    }


async def list_groups(db: AsyncSession, user_id: UUID) -> dict:

    repo = GroupRepository(db)

    groups = await repo.get_user_groups(user_id)

    if groups:
        raise HTTPException(status_code=404, detail="Group not found")

    return {
        "message": "Group fetched successfully",
        "groups": [GroupResponse.model_validate(g) for g in groups],
    }


async def get_group(db: AsyncSession, group_id: UUID) -> dict:

    repo = GroupRepository(db)

    group = await repo.get_by_id(group_id)

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return {"message": "Group found", "group": GroupResponse.model_validate(group)}


async def update_group(
    db: AsyncSession, group_id: UUID, group_data: GroupUpdate, user_id: UUID
) -> dict:

    repo = GroupRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user_id:
        raise HTTPException(
            status_code=403, detail="Only group creator can update the group"
        )

    updated_group = await repo.update(group, group_data.model_dump(exclude_unset=True))

    return {
        "message": "Group updated successfully",
        "group": GroupResponse.model_validate(updated_group),
    }


async def delete_group(group_id: UUID, user_id: UUID, db: AsyncSession) -> dict:

    repo = GroupRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user_id:
        raise HTTPException(
            status_code=403, detail="Only group creator can delete the group"
        )

    await repo.delete(group)

    return {"message": "Group deleted successfully"}


async def add_member(group_id: UUID, user_id: UUID, db: AsyncSession) -> dict:

    repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    existing_user = await member_repo.get(user_id, group_id)
    if existing_user:
        raise HTTPException(
            status_code=400, detail="User is already existing in the group"
        )

    member = await member_repo.add(user_id, group_id)

    return {
        "message": "Member added successfully",
        "member": GroupMemberResponse.model_validate(member),
    }


async def remove_member(group_id: UUID, user_id: UUID, db: AsyncSession) -> dict:

    repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    member = await member_repo.get(user_id, group_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    await member_repo.remove(member)

    return {"message": "Member deleted successfully"}


async def list_members(group_id: UUID, db: AsyncSession) -> dict:

    repo = GroupRepository(db)
    member_repo = GroupMemberRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    members = await member_repo.list_members(group_id)

    return {
        "message": "List of members fetched successfully",
        "members": [GroupMemberResponse.model_validate(m) for m in members],
    }
