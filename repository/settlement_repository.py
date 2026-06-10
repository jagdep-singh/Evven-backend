from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.settlements import Settlement


class SettlementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_settlement(self, settlement: Settlement) -> Settlement:
        self.session.add(settlement)

        await self.session.commit()
        await self.session.refresh(settlement)

        return settlement

    async def update_settlement(self, settlement: Settlement, data: dict) -> Settlement:
        for key, val in data.items():
            setattr(settlement, key, val)

        await self.session.commit()
        await self.session.refresh(settlement)

        return settlement

    async def delete_settlement(self, settlement: Settlement) -> None:
        await self.session.delete(settlement)
        await self.session.commit()

    async def get_settlement_by_id(self, settlement_id: UUID) -> Settlement | None:
        result = await self.session.execute(
            select(Settlement).where(Settlement.id == settlement_id)
        )

        return result.scalar_one_or_none()

    async def get_settlements_by_group_id(self, group_id: UUID) -> list[Settlement]:
        result = await self.session.execute(
            select(Settlement).where(Settlement.group_id == group_id)
        )

        return result.scalars().all()

    # async def get_all_settlement(self) -> list[Settlement]: # for V2 doubtful

    # async def get_settlement_between_users(self) -> list[Settlement]: for V2
