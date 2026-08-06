from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.group_members import GroupMember, Role


class GroupMemberRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_group_member(
        self, user_id: UUID, group_id: UUID, role: Role = Role.MEMBER
    ) -> GroupMember:
        member = GroupMember(group_id=group_id, user_id=user_id, role=role)

        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)

        return member

    async def get_group_member(
        self, user_id: UUID, group_id: UUID
    ) -> GroupMember | None:
        result = await self.session.execute(
            select(GroupMember)
            .options(selectinload(GroupMember.user))
            .where(GroupMember.user_id == user_id, GroupMember.group_id == group_id)
        )

        return result.scalar_one_or_none()

    async def list_group_members(self, group_id: UUID) -> list[GroupMember]:
        result = await self.session.execute(
            select(GroupMember)
            .options(selectinload(GroupMember.user))
            .where(GroupMember.group_id == group_id)
        )

        return list(result.scalars().all())

    async def remove_group_member(self, member: GroupMember) -> None:
        await self.session.delete(member)
        await self.session.commit()

    async def is_member(self, user_id: UUID, group_id: UUID) -> bool:
        result = await self.get_group_member(user_id, group_id)
        return result is not None
