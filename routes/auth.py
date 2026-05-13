from fastapi import APIRouter, Depends, status  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

from deps import get_current_user, get_db
from models.user import User
from schemas.auth import LoginResponse, RegisterResponse
from schemas.user import UserCreate, UserLogin, UserResponse
from services.auth_service import login_user, register_user

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
