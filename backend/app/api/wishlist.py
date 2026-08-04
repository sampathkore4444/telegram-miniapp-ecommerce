from fastapi import APIRouter

from app.api.deps import CurrentUser, DbDep
from app.core.errors import NotFoundError
from app.models import Product, WishlistItem
from app.schemas.wishlist import WishlistAdd

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("", response_model=dict)
async def list_wishlist(user: CurrentUser, db: DbDep):
    from sqlalchemy import select

    result = await db.execute(
        select(WishlistItem)
        .where(WishlistItem.user_id == user.id)
        .order_by(WishlistItem.created_at.desc())
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": w.id,
                "product_id": w.product_id,
                "created_at": w.created_at.isoformat() if w.created_at else None,
                "product": w.product.to_public_dict() if w.product else None,
            }
            for w in items
        ],
        "count": len(items),
    }


@router.post("", response_model=dict)
async def add_wishlist(payload: WishlistAdd, user: CurrentUser, db: DbDep):
    from sqlalchemy import select

    product = await db.get(Product, payload.product_id)
    if product is None or product.status != "active":
        raise NotFoundError("Product not found")

    result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.user_id == user.id, WishlistItem.product_id == payload.product_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        db.add(WishlistItem(user_id=user.id, product_id=payload.product_id))
        await db.commit()
    return {"ok": True}


@router.delete("/{product_id}", response_model=dict)
async def remove_wishlist(product_id: int, user: CurrentUser, db: DbDep):
    from sqlalchemy import select

    result = await db.execute(
        select(WishlistItem).where(
            WishlistItem.user_id == user.id, WishlistItem.product_id == product_id
        )
    )
    item = result.scalar_one_or_none()
    if item is not None:
        await db.delete(item)
        await db.commit()
    return {"ok": True}
