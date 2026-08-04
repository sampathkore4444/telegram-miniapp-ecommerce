from decimal import Decimal

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentAdmin, DbDep
from app.api.orders import order_to_public
from app.core.errors import AppError, NotFoundError
from app.models import Order, OrderStatus, PaymentMethod, User
from app.schemas.order import OrderStatusUpdate, RefundRequest
from app.services.orders import (
    change_order_status,
    get_order_or_404,
    get_store_settings,
    refund_order,
)
from app.services.notifications import notify_buyer_order_update

router = APIRouter(prefix="/admin/orders", tags=["admin"])


@router.get("", response_model=dict)
async def admin_list_orders(
    db: DbDep,
    admin: CurrentAdmin,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: OrderStatus | None = None,
    payment_method: PaymentMethod | None = None,
    search: str | None = None,
    order_number: str | None = None,
):
    stmt = select(Order)
    count_stmt = select(func.count(Order.id))
    if status:
        stmt = stmt.where(Order.status == status)
        count_stmt = count_stmt.where(Order.status == status)
    if payment_method:
        stmt = stmt.where(Order.payment_method == payment_method)
        count_stmt = count_stmt.where(Order.payment_method == payment_method)
    if order_number:
        stmt = stmt.where(Order.order_number.ilike(f"%{order_number.strip()}%"))
        count_stmt = count_stmt.where(Order.order_number.ilike(f"%{order_number.strip()}%"))
    if search:
        stmt = stmt.where(
            (Order.recipient_name.ilike(f"%{search.strip()}%"))
            | (Order.recipient_phone.ilike(f"%{search.strip()}%"))
        )
        count_stmt = count_stmt.where(
            (Order.recipient_name.ilike(f"%{search.strip()}%"))
            | (Order.recipient_phone.ilike(f"%{search.strip()}%"))
        )

    total = (await db.execute(count_stmt)).scalar() or 0
    pages = (total + page_size - 1) // page_size
    result = await db.execute(
        stmt.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    orders = result.scalars().all()
    items = []
    for order in orders:
        d = order_to_public(order).model_dump()
        user = await db.get(User, order.user_id)
        d["customer"] = (
            {"telegram_id": user.telegram_id, "display_name": user.display_name}
            if user
            else None
        )
        items.append(d)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


@router.get("/{order_id}", response_model=dict)
async def admin_get_order(order_id: int, db: DbDep, admin: CurrentAdmin):
    order = await get_order_or_404(db, order_id)
    d = order_to_public(order).model_dump()
    user = await db.get(User, order.user_id)
    d["customer"] = (
        {"telegram_id": user.telegram_id, "display_name": user.display_name}
        if user
        else None
    )
    return d


@router.patch("/{order_id}/status", response_model=dict)
async def admin_update_order_status(
    order_id: int, payload: OrderStatusUpdate, db: DbDep, admin: CurrentAdmin
):
    order = await get_order_or_404(db, order_id)
    if order.status == payload.status:
        raise AppError("Order is already in this status.", code="same_status")

    order = await change_order_status(db, order, payload.status, admin.id, payload.note)
    if order.payment_status.value == "paid" and order.paid_at is None:
        import datetime as dt

        order.paid_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()

    store = await get_store_settings(db)
    user = await db.get(User, order.user_id)
    if user:
        await notify_buyer_order_update(order, user, store)

    refreshed = await get_order_or_404(db, order_id)
    d = order_to_public(refreshed).model_dump()
    d["customer"] = (
        {"telegram_id": user.telegram_id, "display_name": user.display_name} if user else None
    )
    return d


@router.post("/{order_id}/refund", response_model=dict)
async def admin_refund_order(
    order_id: int, payload: RefundRequest, db: DbDep, admin: CurrentAdmin
):
    order = await get_order_or_404(db, order_id)
    order = await refund_order(db, order, Decimal(str(payload.amount)), payload.reason, admin.id)
    await db.commit()

    store = await get_store_settings(db)
    user = await db.get(User, order.user_id)
    if user:
        await notify_buyer_order_update(order, user, store)

    refreshed = await get_order_or_404(db, order_id)
    d = order_to_public(refreshed).model_dump()
    d["customer"] = (
        {"telegram_id": user.telegram_id, "display_name": user.display_name} if user else None
    )
    return d
