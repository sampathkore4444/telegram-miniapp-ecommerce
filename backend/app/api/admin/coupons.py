import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.deps import AdminStore, DbDep, require_feature
from app.core.errors import ConflictError, NotFoundError
from app.models import DiscountCode, User
from app.schemas.common import Page
from app.schemas.discount import DiscountCodeCreate, DiscountCodePublic, DiscountCodeUpdate

router = APIRouter(prefix="/admin/coupons", tags=["admin"])

CouponAdmin = Annotated[User, Depends(require_feature("coupons"))]


def _to_public(coupon: DiscountCode) -> DiscountCodePublic:
    return DiscountCodePublic(
        id=coupon.id,
        code=coupon.code,
        discount_type=coupon.discount_type,
        value=float(coupon.value),
        min_subtotal=float(coupon.min_subtotal),
        max_uses=coupon.max_uses,
        used_count=coupon.used_count,
        per_user_limit=coupon.per_user_limit,
        active_from=coupon.active_from,
        active_until=coupon.active_until,
        is_active=coupon.is_active,
    )


def _normalize_datetime(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value


@router.get("", response_model=Page[dict])
async def admin_list_coupons(
    db: DbDep,
    store: AdminStore,
    admin: CouponAdmin,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    active_only: bool = False,
):
    stmt = select(DiscountCode).where(DiscountCode.store_id == store.id)
    if active_only:
        stmt = stmt.where(DiscountCode.is_active.is_(True))
    if search:
        stmt = stmt.where(DiscountCode.code.ilike(f"%{search.strip().upper()}%"))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    pages = (total + page_size - 1) // page_size
    result = await db.execute(
        stmt.order_by(DiscountCode.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_public(c).model_dump(mode="json") for c in result.scalars().all()]
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model=dict)
async def admin_create_coupon(payload: DiscountCodeCreate, db: DbDep, store: AdminStore, admin: CouponAdmin):
    data = payload.model_dump()
    data["code"] = data["code"].strip().upper()
    existing = await db.execute(
        select(DiscountCode).where(
            DiscountCode.code == data["code"], DiscountCode.store_id == store.id
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A coupon with this code already exists.")
    data["active_from"] = _normalize_datetime(data.get("active_from"))
    data["active_until"] = _normalize_datetime(data.get("active_until"))
    coupon = DiscountCode(**data, store_id=store.id)
    db.add(coupon)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise ConflictError("A coupon with this code already exists.")
    await db.refresh(coupon)
    return _to_public(coupon).model_dump(mode="json")


@router.patch("/{coupon_id}", response_model=dict)
async def admin_update_coupon(
    coupon_id: int, payload: DiscountCodeUpdate, db: DbDep, store: AdminStore, admin: CouponAdmin
):
    coupon = await db.get(DiscountCode, coupon_id)
    if coupon is None or coupon.store_id != store.id:
        raise NotFoundError("Coupon not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("code") is not None:
        new_code = data["code"].strip().upper()
        dup = await db.execute(
            select(DiscountCode).where(
                DiscountCode.code == new_code,
                DiscountCode.store_id == store.id,
                DiscountCode.id != coupon_id,
            )
        )
        if dup.scalar_one_or_none() is not None:
            raise ConflictError("A coupon with this code already exists.")
        data["code"] = new_code
    if "active_from" in data:
        data["active_from"] = _normalize_datetime(data["active_from"])
    if "active_until" in data:
        data["active_until"] = _normalize_datetime(data["active_until"])
    for key, value in data.items():
        setattr(coupon, key, value)
    await db.commit()
    await db.refresh(coupon)
    return _to_public(coupon).model_dump(mode="json")


@router.delete("/{coupon_id}", status_code=204)
async def admin_delete_coupon(coupon_id: int, db: DbDep, store: AdminStore, admin: CouponAdmin):
    coupon = await db.get(DiscountCode, coupon_id)
    if coupon is None or coupon.store_id != store.id:
        raise NotFoundError("Coupon not found")
    await db.delete(coupon)
    await db.commit()
