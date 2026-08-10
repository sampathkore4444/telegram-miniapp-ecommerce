from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentAdmin, DbDep
from app.core.errors import ConflictError, NotFoundError
from app.core.plans import ensure_feature
from app.models import (
    CartItem,
    Category,
    DiscountCode,
    Order,
    Product,
    ProductReview,
    RecentlyViewed,
    StockAlert,
    Store,
    StoreSettings,
    WishlistItem,
)
from app.schemas.store import StoreCreate, StorePublic, StoreUpdate
from app.services.plans import store_plan_payload
from app.services.stores import (
    _create_store,
    _unique_store_slug,
    list_owner_stores,
)

router = APIRouter(prefix="/admin/stores", tags=["admin"])

# Tables holding per-store tenant data that block store deletion.
TENANT_MODELS = [
    Product,
    Category,
    DiscountCode,
    Order,
    CartItem,
    WishlistItem,
    ProductReview,
    StockAlert,
    RecentlyViewed,
]


async def _owned_store(db: DbDep, store_id: int, owner_id: int) -> Store:
    store = await db.get(Store, store_id)
    if store is None or store.owner_id != owner_id:
        raise NotFoundError("Store not found")
    return store


async def _public(db: DbDep, store: Store) -> dict:
    product_count = (
        await db.execute(
            select(func.count(Product.id)).where(Product.store_id == store.id)
        )
    ).scalar() or 0
    data = store.to_dict()
    data["product_count"] = product_count
    data.update(await store_plan_payload(db, store))
    return data


@router.get("", response_model=list[StorePublic])
async def admin_list_stores(db: DbDep, admin: CurrentAdmin):
    """All stores owned by the admin, used by the store switcher."""
    stores = await list_owner_stores(db, admin.id)
    return [await _public(db, store) for store in stores]


@router.post("", response_model=StorePublic)
async def admin_create_store(payload: StoreCreate, db: DbDep, admin: CurrentAdmin):
    """Create a new store. The first store is always allowed; an additional
    store requires the Pro ``multi_store`` feature."""
    owned = await list_owner_stores(db, admin.id)
    if owned:
        ensure_feature(admin.plan, "multi_store")
    store = await _create_store(
        db, admin, payload.name.strip(), slug=payload.slug
    )
    await db.commit()
    await db.refresh(store)
    return await _public(db, store)


@router.get("/{store_id}", response_model=StorePublic)
async def admin_get_store(store_id: int, db: DbDep, admin: CurrentAdmin):
    store = await _owned_store(db, store_id, admin.id)
    return await _public(db, store)


@router.patch("/{store_id}", response_model=StorePublic)
async def admin_update_store(
    store_id: int, payload: StoreUpdate, db: DbDep, admin: CurrentAdmin
):
    store = await _owned_store(db, store_id, admin.id)
    data = payload.model_dump(exclude_unset=True)
    name = data.pop("name", None)
    if name is not None:
        data["name"] = name.strip()
    slug = data.pop("slug", None)
    if slug is not None:
        data["slug"] = await _unique_store_slug(db, slug, exclude_id=store.id)
    for key, value in data.items():
        setattr(store, key, value)
    if store.name:
        settings = (
            await db.execute(
                select(StoreSettings).where(StoreSettings.store_id == store.id)
            )
        ).scalar_one_or_none()
        if settings is not None and settings.store_name != store.name:
            settings.store_name = store.name
    await db.commit()
    await db.refresh(store)
    return await _public(db, store)


@router.delete("/{store_id}", status_code=204)
async def admin_delete_store(store_id: int, db: DbDep, admin: CurrentAdmin):
    store = await _owned_store(db, store_id, admin.id)
    for model in TENANT_MODELS:
        count = (
            await db.execute(
                select(func.count()).select_from(model).where(model.store_id == store.id)
            )
        ).scalar() or 0
        if count:
            raise ConflictError(
                "This store still has products, orders, or other data. "
                "Archive it (set inactive) instead."
            )
    settings = await db.execute(
        select(StoreSettings).where(StoreSettings.store_id == store.id)
    )
    for row in settings.scalars().all():
        await db.delete(row)
    await db.delete(store)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            "This store still has products, orders, or other data. "
            "Archive it (set inactive) instead."
        )
