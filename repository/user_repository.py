from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from models.password_reset_token import PasswordResetToken
from models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_google_id(self, google_id: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.commit()

    async def get_user_by_user_code(self, user_code: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.user_code == user_code)
        )
        return result.scalar_one_or_none()


class AuthRepository:
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
                not PasswordResetToken.used,
                PasswordResetToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def mark_token_as_used(self, reset_record: PasswordResetToken) -> None:
        reset_record.used = True
        await self.session.commit()

    async def delete_token(self, user_id: UUID) -> None:
        # removed all used tokens for a user.
        result = await self.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used,
            )
        )

        for record in result.scalars().all():
            await self.session.delete(record)
        await self.session.commit()
