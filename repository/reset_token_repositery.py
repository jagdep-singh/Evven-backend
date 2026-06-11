from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from models.password_reset_token import PasswordResetToken


class ResetRepositery:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_reset_token(
        self, user_id: UUID, token_hash: str, expire_at: datetime
    ) -> PasswordResetToken:
        reset_token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expire_at=expire_at,
        )
        self.session.add(reset_token)
        await self.session.commit()
        await self.session.refresh(reset_token)

        return reset_token

    async def get_valid_reset_token(self, token_hash: str) -> PasswordResetToken:
        result = await self.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used.is_(False),
                PasswordResetToken.expire_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def mark_token_as_used(self, reset_record: PasswordResetToken) -> None:
        reset_record.used = True
        await self.session.commit()

    async def delete_token(self):
        # removed all used tokens for a user.
        await self.session.execute(
            delete(PasswordResetToken).where(
                PasswordResetToken.expire_at < datetime.now(timezone.utc),
                PasswordResetToken.used.is_(True),
            )
        )
        await self.session.commit()

        # result = await self.session.execute(
        #     select(PasswordResetToken).where(
        #         PasswordResetToken.user_id == user_id,
        #         PasswordResetToken.used.is_(True),
        #     )
        # )

        # for record in result.scalars().all():
        #     await self.session.delete(record)
        # await self.session.commit()
