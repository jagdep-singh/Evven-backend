from fastapi import APIRouter, Body, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.auth import (
    ForgotPasswordRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterResponse,
    ResetPasswordRequest,
)
from schemas.user import (
    GoogleAuthRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from services.auth_service import (
    google_login,
    login_user,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)
from services.reset_password_service import (
    request_password_reset,
    reset_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await register_user(user_data, db)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    return await login_user(login_data, db)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def read_current_user(user: User = Depends(get_current_user)):
    return user


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    refresh_data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    return await rotate_refresh_token(refresh_data.refresh_token, db)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    refresh_data: RefreshTokenRequest | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if refresh_data:
        await revoke_refresh_token(refresh_data.refresh_token, db)
    return {"message": "Logged out successfully"}


@router.get("/forgot-password", include_in_schema=False)
def forget_password():
    return FileResponse("templates/forget-password.html")


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def request_password(
    body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    return await request_password_reset(body.email, db)


@router.get("/reset-password")
def reset_password_page(token: str):
    return FileResponse("templates/password-reset.html")


@router.put("/reset-password")
async def update_password(
    body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    return await reset_password(body.token, body.password, db)


@router.post("/google", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    return await google_login(body, db)
