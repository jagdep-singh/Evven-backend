from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from repository.user_repository import UserRepository
from services.auth_service import decode_token


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials

    payload = decode_token(token, expected_type="access")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    repo = UserRepository(db)

    try:
        user_uuid = UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await repo.get_user_by_id(user_uuid)

    if not user or not user.is_active or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive, unverified, or invalid user",
        )
    return user


# ops logging — optional auth for error ingestion
security_optional = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security_optional),
    db: AsyncSession = Depends(get_db),
):
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token, expected_type="access")

    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    repo = UserRepository(db)

    try:
        user_uuid = UUID(user_id)
    except (ValueError, AttributeError):
        return None

    user = await repo.get_user_by_id(user_uuid)

    if not user or not user.is_active or not user.is_verified:
        return None

    return user


# end ops logging
