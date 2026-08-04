from fastapi import APIRouter

from app.api.deps import CurrentUser, DbDep
from app.models import User
from app.schemas.user import UserPublic, UserUpdate

router = APIRouter(prefix="/me", tags=["users"])


@router.get("", response_model=UserPublic)
async def get_profile(user: CurrentUser):
    return UserPublic.model_validate(user)


@router.patch("", response_model=UserPublic)
async def update_profile(payload: UserUpdate, user: CurrentUser, db: DbDep):
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return UserPublic.model_validate(user)
