from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        token_id: UUID,
        user_id: UUID,
        token_hash: str,
        family_id: UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        refresh_token = RefreshToken(
            id=token_id,
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self.session.add(refresh_token)
        await self.session.commit()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_by_id(self, token_id: UUID) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.id == token_id)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken, revoked_at: datetime) -> None:
        token.revoked_at = revoked_at
        await self.session.commit()

    async def rotate(
        self,
        *,
        current_token: RefreshToken,
        new_token_id: UUID,
        new_token_hash: str,
        new_expires_at: datetime,
        revoked_at: datetime,
    ) -> RefreshToken:
        current_token.revoked_at = revoked_at
        new_token = RefreshToken(
            id=new_token_id,
            user_id=current_token.user_id,
            token_hash=new_token_hash,
            family_id=current_token.family_id,
            expires_at=new_expires_at,
        )
        self.session.add(new_token)
        await self.session.commit()
        await self.session.refresh(new_token)
        return new_token

    async def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .values(revoked_at=revoked_at)
        )
        await self.session.commit()

    async def delete_expired_before(self, cutoff: datetime) -> None:
        await self.session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < cutoff)
        )
        await self.session.commit()
