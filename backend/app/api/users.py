from fastapi import APIRouter

from app.api.deps import CurrentUser, DbDep
from app.models import Product, RecentlyViewed, User
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


@router.get("/recently-viewed", response_model=dict)
async def list_recently_viewed(user: CurrentUser, db: DbDep, limit: int = 10):
    """Products the buyer viewed recently, most recent first."""
    from sqlalchemy import select

    limit = max(1, min(limit, 30))
    stmt = (
        select(Product)
        .join(RecentlyViewed, RecentlyViewed.product_id == Product.id)
        .where(RecentlyViewed.user_id == user.id, Product.status == "active")
        .order_by(RecentlyViewed.viewed_at.desc())
        .limit(limit)
    )
    products = (await db.execute(stmt)).scalars().all()
    return {"items": [p.to_public_dict() for p in products]}
