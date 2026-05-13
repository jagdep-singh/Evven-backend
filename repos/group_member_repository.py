from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.group_members import GroupMember


class GroupMemberRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: UUID, group_id: UUID) -> GroupMember:

        member = GroupMember(group_id=group_id, user_id=user_id)

        await self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)

        return member

    async def get(self, user_id: UUID, group_id: UUID) -> GroupMember | None:

        return await self.session.execute(
            select(GroupMember).where(
                GroupMember.user_id == user_id, GroupMember.group_id == group_id
            )
        )

    async def list_members(self, group_id: UUID) -> list[GroupMember]:

        result = await self.session.execute(
            select(GroupMember).where(GroupMember.group_id == group_id)
        )

        return list(result.scalars().all())

    async def remove(self, member: GroupMember) -> None:

        await self.session.delete(member)
        await self.session.commit()
