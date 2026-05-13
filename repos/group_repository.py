from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.group_members import GroupMember
from models.groups import Group


class GroupRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Group:

        group = Group(**data)

        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)

        return group

    async def get_by_id(self, group_id: UUID) -> Group | None:

        result = await self.session.execute(select(Group).where(Group.id == group_id))

        return result.scalar_one_or_none()

    async def get_user_groups(self, user_id: UUID) -> list[Group]:

        result = await self.session.execute(
            select(Group).join(GroupMember).where(GroupMember.user_id == user_id)
        )

        return list(result.scalars().all())

    async def update(self, group: Group, data: dict) -> Group:

        for key, val in data.items():
            setattr(group, key, val)

        await self.session.commit()
        await self.session.refresh(group)

        return group

    async def delete(self, group: Group) -> None:
        await self.session.delete(group)
        await self.session.commit()
