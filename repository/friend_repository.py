from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.group_members import GroupMember, Role
from models.groups import Group, GroupStatus, GroupType


class FriendRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    """
    this function return the group between user_a and user_b
    """

    async def find_friend_group_between_users(
        self, user_a_id: UUID, user_b_id: UUID
    ) -> Group | None:
        stmt = (
            select(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .where(
                GroupMember.user_id == user_b_id,
                Group.id.in_(
                    select(GroupMember.group_id).where(GroupMember.user_id == user_a_id)
                ),
                Group.group_type == GroupType.FRIEND,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()

    """
    this group returns list of group created by user varying their status
    means dev who are writing the service can give para like status1, status2 in statuses the 
    function will return all the group associated with user_id with given status
    if statuses left None or empty the function will return all groups with appicable status in GroupStatus Enum
    
    limit is used to limit output for function call
    offset is for how many item we want to left
    means offset = 0 left 0 items
    10 will not show top 10 items
    
    it is useful in pagination otherwise no matter how many page we will change it always start with 1st item  
    """

    async def list_friend_groups_by_user_and_status(
        self,
        user_id: UUID,
        statuses: list[GroupStatus] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Group]:

        # Main Query
        stmt = (
            select(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .where(
                Group.group_type == GroupType.FRIEND,
                GroupMember.user_id == user_id,
            )
        )

        if statuses:
            stmt = stmt.where(Group.status.in_(statuses))

        stmt = stmt.order_by(Group.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    """
    Creates friends group with req_id and reci_id with both being Admin
    """

    async def create_pending_friend_group(
        self,
        requester_id: UUID,
        recipient_id: UUID,
    ) -> Group:

        group = Group(
            name=f"Friend-{requester_id}-{recipient_id}",
            created_by=requester_id,
            group_type=GroupType.FRIEND,
            status=GroupStatus.PENDING,
        )

        self.session.add(group)
        await self.session.flush()

        member1 = GroupMember(group_id=group.id, user_id=requester_id, role=Role.ADMIN)
        member2 = GroupMember(group_id=group.id, user_id=recipient_id, role=Role.ADMIN)

        self.session.add_all([member1, member2])

        await self.session.commit()
        await self.session.refresh(group)
        return group

    """
    update status of group 
    like fro pending to active if recipient accept the invite
    """

    async def update_status(
        self,
        group: Group,
        new_status: GroupStatus,
    ) -> Group:

        group.status = new_status
        await self.session.commit()
        await self.session.refresh(group)
        return group

    """
    delete the friend group
    first remove groupmember from group then delete the group
    to avoid unneccary error
    """

    async def hard_delete_pending_group(self, group: Group) -> None:
        await self.session.execute(
            delete(GroupMember).where(GroupMember.group_id == group.id)
        )

        await self.session.delete(group)
        await self.session.commit()
