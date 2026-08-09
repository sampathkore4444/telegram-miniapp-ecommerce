"""Public store directory: lists the stores buyers can browse."""
from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DbDep
from app.models import Product, Store
from app.services.plans import store_plan_payload

router = APIRouter(prefix="/stores", tags=["store"])


async def _public(db: DbDep, store: Store) -> dict:
    product_count = (
        await db.execute(
            select(func.count(Product.id)).where(
                Product.store_id == store.id, Product.status == "active"
            )
        )
    ).scalar() or 0
    settings = store.settings
    plan_payload = await store_plan_payload(db, store)
    return {
        "id": store.id,
        "name": store.name,
        "slug": store.slug,
        "store_name": settings.store_name if settings else store.name,
        "description": (
            settings.store_description or settings.welcome_message if settings else None
        ),
        "product_count": product_count,
        "plan": plan_payload["plan"],
    }


@router.get("", response_model=list[dict])
async def public_store_directory(db: DbDep):
    """Active stores, sorted by catalog size then name. No auth required."""
    result = await db.execute(
        select(Store).where(Store.is_active.is_(True)).order_by(Store.name.asc())
    )
    stores = list(result.scalars().all())
    rows = [await _public(db, store) for store in stores]
    rows.sort(key=lambda s: (-s["product_count"], s["name"].lower()))
    return rows
