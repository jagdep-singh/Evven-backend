from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, desc, select  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from models.email_verification_token import EmailVerificationToken


class EmailVerificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_latest_valid_token(
        self, user_id: UUID
    ) -> EmailVerificationToken | None:
        result = await self.session.execute(
            select(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used.is_(False),
                EmailVerificationToken.expires_at > datetime.now(timezone.utc),
            )
            .order_by(desc(EmailVerificationToken.created_at))
        )
        return result.scalars().first()

    async def mark_token_as_used(self, token: EmailVerificationToken) -> None:
        token.used = True
        await self.session.commit()

    async def delete_token(self, token: EmailVerificationToken) -> None:
        await self.session.delete(token)
        await self.session.commit()

    async def delete_tokens_for_user(self, user_id: UUID) -> None:
        await self.session.execute(
            delete(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id
            )
        )
        await self.session.commit()
