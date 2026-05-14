from fastapi import APIRouter, Depends , status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.user import User
from repos.user_repository import UserRepository
from schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    user: User = Depends(get_current_user),
):
    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)

    update_data = user_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    updated_user = await repo.update_user(user)

    return updated_user

@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_account(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.is_active = False
    await UserRepository(db).update_user(user)
    return {"message": "Account deactivated successfully"}