from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status  
from sqlalchemy.ext.asyncio import AsyncSession  

from repos.user_repository import UserRepository
from core.deps import get_current_user, get_db
from models.user import User
from schemas.auth import LoginResponse, RefreshTokenRequest, RegisterResponse
from schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from services.auth_service import create_access_token, create_refresh_token, decode_token, login_user, register_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await register_user(user_data, db)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    return await login_user(login_data, db)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def read_current_user(user: User = Depends(get_current_user)):
    return user

@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(refresh_data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(refresh_data.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    repo = UserRepository(db)
    user = await repo.get_user_by_id(UUID(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_payload = {"sub": str(user.id)}
    access_token = create_access_token(new_payload)
    refresh_token = create_refresh_token(new_payload)

    return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
    
@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully"}

