from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.api.deps import ActiveStore, CurrentUser, DbDep, OptionalUser
from app.core.errors import AppError, NotFoundError
from app.models import Category, Product, ProductVariant, RecentlyViewed, StockAlert
from app.schemas.catalog import ProductCreate, ProductUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/products", tags=["catalog"])


class StockAlertRequest(BaseModel):
    variant_id: int | None = None


@router.get("", response_model=Page[dict])
async def list_products(
    db: DbDep,
    store: ActiveStore,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    search: str | None = None,
    featured: bool | None = None,
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|popular)$"),
):
    stmt = select(Product).where(Product.store_id == store.id, Product.status == "active")
    if category:
        cat_result = await db.execute(
            select(Category).where(Category.slug == category, Category.store_id == store.id)
        )
        cat = cat_result.scalar_one_or_none()
        if cat:
            stmt = stmt.where(Product.category_id == cat.id)
        else:
            return Page(items=[], total=0, page=page, page_size=page_size, pages=0)
    if search:
        term = search.strip()
        stmt = stmt.where(
            or_(
                Product.name.ilike(f"%{term}%"),
                Product.description.ilike(f"%{term}%"),
                Product.sku.ilike(f"%{term}%"),
            )
        )
    if featured is not None:
        stmt = stmt.where(Product.is_featured.is_(featured))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    pages = (total + page_size - 1) // page_size

    if sort == "price_asc":
        stmt = stmt.order_by(Product.price.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(Product.price.desc())
    elif sort == "popular":
        stmt = stmt.order_by(Product.sold_count.desc())
    else:
        stmt = stmt.order_by(Product.created_at.desc())

    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    items = [p.to_public_dict() for p in result.scalars().all()]
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/{product_id}", response_model=dict)
async def get_product(product_id: int, db: DbDep, store: ActiveStore, user: OptionalUser = None):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.store_id == store.id)
    )
    product = result.scalar_one_or_none()
    if product is None or product.status != "active":
        raise NotFoundError("Product not found")

    if user is not None and not user.is_admin:
        existing = (
            await db.execute(
                select(RecentlyViewed).where(
                    RecentlyViewed.user_id == user.id,
                    RecentlyViewed.product_id == product.id,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                RecentlyViewed(
                    user_id=user.id, product_id=product.id, store_id=store.id
                )
            )
        else:
            import datetime as dt

            existing.viewed_at = dt.datetime.now(dt.timezone.utc)
        await db.commit()

    return product.to_public_dict()


@router.post("/{product_id}/stock-alert", response_model=dict)
async def create_stock_alert(
    product_id: int,
    payload: StockAlertRequest,
    user: CurrentUser,
    db: DbDep,
    store: ActiveStore,
):
    """Subscribe to a back-in-stock notification for a product (or variant)."""
    product = await db.get(Product, product_id)
    if product is None or product.status != "active" or product.store_id != store.id:
        raise NotFoundError("Product not found")

    variant = None
    if payload.variant_id is not None:
        variant = await db.get(ProductVariant, payload.variant_id)
        if variant is None or variant.product_id != product.id:
            raise NotFoundError("Variant not found")

    available = variant.stock if variant else product.stock
    if available > 0:
        raise AppError("This item is in stock already.", code="in_stock_already")

    result = await db.execute(
        select(StockAlert).where(
            StockAlert.user_id == user.id,
            StockAlert.product_id == product.id,
            StockAlert.variant_id == payload.variant_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        db.add(
            StockAlert(
                user_id=user.id,
                product_id=product.id,
                store_id=store.id,
                variant_id=payload.variant_id,
            )
        )
        await db.commit()
    return {"ok": True}


@router.delete("/{product_id}/stock-alert", response_model=dict)
async def delete_stock_alert(
    product_id: int, user: CurrentUser, db: DbDep, store: ActiveStore
):
    result = await db.execute(
        select(StockAlert).where(
            StockAlert.user_id == user.id,
            StockAlert.product_id == product_id,
            StockAlert.store_id == store.id,
        )
    )
    item = result.scalar_one_or_none()
    if item is not None:
        await db.delete(item)
        await db.commit()
    return {"ok": True}
