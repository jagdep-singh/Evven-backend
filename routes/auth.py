from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import (
    FORGOT_PASSWORD_BUCKET_CAPACITY,
    FORGOT_PASSWORD_REFILL_RATE,
    GOOGLE_AUTH_BUCKET_CAPACITY,
    GOOGLE_AUTH_REFILL_RATE,
    RESET_PASSWORD_BUCKET_CAPACITY,
    RESET_PASSWORD_PAGE_BUCKET_CAPACITY,
    RESET_PASSWORD_PAGE_REFILL_RATE,
    RESET_PASSWORD_REFILL_RATE,
)
from core.deps import get_current_user, get_db
from core.rate_limiter import create_rate_limiter

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


# -------------------------------------------------------------------
# Rate limiters
# -------------------------------------------------------------------

forgot_password_limiter = create_rate_limiter(
    capacity=FORGOT_PASSWORD_BUCKET_CAPACITY,
    refill_rate=FORGOT_PASSWORD_REFILL_RATE,
)

reset_password_page_limiter = create_rate_limiter(
    capacity=RESET_PASSWORD_PAGE_BUCKET_CAPACITY,
    refill_rate=RESET_PASSWORD_PAGE_REFILL_RATE,
)

reset_password_limiter = create_rate_limiter(
    capacity=RESET_PASSWORD_BUCKET_CAPACITY,
    refill_rate=RESET_PASSWORD_REFILL_RATE,
)

google_auth_limiter = create_rate_limiter(
    capacity=GOOGLE_AUTH_BUCKET_CAPACITY,
    refill_rate=GOOGLE_AUTH_REFILL_RATE,
)


# -------------------------------------------------------------------
# Authentication
# -------------------------------------------------------------------

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db),
):
    return await register_user(user_data, db)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
        login_data: UserLogin,
        db: AsyncSession = Depends(get_db),
):
    return await login_user(login_data, db)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def read_current_user(
        user: User = Depends(get_current_user),
):
    return user


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(
        refresh_data: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db),
):
    return await rotate_refresh_token(
        refresh_data.refresh_token,
        db,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
async def logout(
        refresh_data: RefreshTokenRequest,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    await revoke_refresh_token(
        refresh_data.refresh_token,
        db,
        user_id=user.id,
    )

    return {"message": "Logged out successfully"}


# -------------------------------------------------------------------
# Forgot password
# -------------------------------------------------------------------

@router.get(
    "/forgot-password",
    include_in_schema=False,
)
def forget_password():
    return FileResponse("templates/forget-password.html")


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
)
async def request_password(
        body: ForgotPasswordRequest,
        db: AsyncSession = Depends(get_db),
        _: None = Depends(forgot_password_limiter),
):
    return await request_password_reset(
        body.email,
        db,
    )


# -------------------------------------------------------------------
# Reset password
# -------------------------------------------------------------------

@router.get("/reset-password")
def reset_password_page(
        token: str,
        _: None = Depends(reset_password_page_limiter),
):
    return FileResponse("templates/password-reset.html")


@router.put("/reset-password")
async def update_password(
        body: ResetPasswordRequest,
        db: AsyncSession = Depends(get_db),
        _: None = Depends(reset_password_limiter),
):
    return await reset_password(
        body.token,
        body.password,
        db,
    )


# -------------------------------------------------------------------
# Google authentication
# -------------------------------------------------------------------

@router.post(
    "/google",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def google_auth(
        body: GoogleAuthRequest,
        db: AsyncSession = Depends(get_db),
        _: None = Depends(google_auth_limiter),
):
    return await google_login(
        body,
        db,
    )