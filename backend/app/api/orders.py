from fastapi import APIRouter, Form, Query, UploadFile

from app.api.deps import CurrentUser, DbDep
from app.core.errors import AppError, NotFoundError
from app.models import CANCELLABLE_STATUSES, CartItem, Order, OrderStatus, PaymentMethod, PaymentStatus
from app.schemas.cart import CartPublic
from app.schemas.order import CheckoutRequest, OrderPublic, PaymentProofRequest
from app.services.orders import (
    change_order_status,
    create_order,
    get_order_or_404,
    get_store_settings,
    submit_payment_proof as services_submit_payment_proof,
)
from app.services.notifications import notify_buyer_order_update
from app.services.uploads import save_upload

router = APIRouter(prefix="/orders", tags=["orders"])


def order_to_public(order: Order) -> OrderPublic:
    return OrderPublic(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        receipt_image=order.receipt_image,
        transaction_ref=order.transaction_ref,
        paid_at=order.paid_at.isoformat() if order.paid_at else None,
        subtotal=float(order.subtotal),
        delivery_fee=float(order.delivery_fee),
        discount=float(order.discount),
        total=float(order.total),
        coupon_code=order.coupon_code,
        recipient_name=order.recipient_name,
        recipient_phone=order.recipient_phone,
        delivery_address=order.delivery_address,
        delivery_note=order.delivery_note,
        cancel_reason=order.cancel_reason,
        admin_note=order.admin_note,
        refund_amount=float(order.refund_amount) if order.refund_amount is not None else None,
        refund_reason=order.refund_reason,
        refunded_at=order.refunded_at.isoformat() if order.refunded_at else None,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[i.to_dict() for i in order.items],
        status_logs=[s.to_dict() for s in order.status_logs],
    )


async def _get_my_order(db: DbDep, order_id: int, user) -> Order:
    order = await get_order_or_404(db, order_id, user)
    return order


@router.post("/checkout", response_model=OrderPublic)
async def checkout(payload: CheckoutRequest, user: CurrentUser, db: DbDep):
    from sqlalchemy import select

    result = await db.execute(select(CartItem).where(CartItem.user_id == user.id))
    cart_items = result.scalars().all()
    if not cart_items:
        raise AppError("Your cart is empty.", code="empty_cart")

    order = await create_order(db, user, payload, cart_items)

    for item in cart_items:
        await db.delete(item)
    await db.commit()

    # refresh to load relationships with committed data
    refreshed = await get_order_or_404(db, order.id)
    try:
        store = await get_store_settings(db)
        await notify_buyer_order_update(
            refreshed,
            user,
            store,
            message=(
                f"Your order {refreshed.order_number} has been received. "
                f"Total: {store.currency_symbol}{float(refreshed.total):.2f}."
            ),
        )
    except Exception:  # notifications are best-effort
        pass
    return order_to_public(refreshed)


@router.get("", response_model=dict)
async def list_my_orders(
    user: CurrentUser,
    db: DbDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: OrderStatus | None = None,
):
    from sqlalchemy import func, select

    stmt = select(Order).where(Order.user_id == user.id)
    count_stmt = select(func.count(Order.id)).where(Order.user_id == user.id)
    if status:
        stmt = stmt.where(Order.status == status)
        count_stmt = count_stmt.where(Order.status == status)

    total = (await db.execute(count_stmt)).scalar() or 0
    pages = (total + page_size - 1) // page_size
    result = await db.execute(
        stmt.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [order_to_public(o) for o in result.scalars().all()]
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


@router.get("/{order_id}", response_model=OrderPublic)
async def get_my_order(order_id: int, user: CurrentUser, db: DbDep):
    order = await _get_my_order(db, order_id, user)
    return order_to_public(order)


@router.post("/{order_id}/cancel", response_model=OrderPublic)
async def cancel_my_order(order_id: int, user: CurrentUser, db: DbDep):
    order = await _get_my_order(db, order_id, user)
    if order.status not in CANCELLABLE_STATUSES:
        raise AppError(
            "This order can no longer be cancelled.", code="order_not_cancellable"
        )
    order = await change_order_status(
        db, order, OrderStatus.CANCELLED, user.id, note="Cancelled by buyer"
    )
    await db.commit()
    refreshed = await get_order_or_404(db, order_id)
    try:
        store = await get_store_settings(db)
        await notify_buyer_order_update(
            refreshed, user, store, message=f"Your order {refreshed.order_number} was cancelled."
        )
    except Exception:  # notifications are best-effort
        pass
    return order_to_public(refreshed)


@router.post("/{order_id}/payment-proof", response_model=OrderPublic)
async def submit_payment_proof(
    order_id: int,
    user: CurrentUser,
    db: DbDep,
    transaction_ref: str = Form(min_length=3, max_length=128),
    receipt: UploadFile | None = None,
):
    order = await _get_my_order(db, order_id, user)
    receipt_image = None
    if receipt is not None:
        receipt_image = await save_upload(receipt, "receipts")

    order = await services_submit_payment_proof(
        db, order, user, transaction_ref.strip(), receipt_image
    )
    await db.commit()
    refreshed = await get_order_or_404(db, order_id)
    return order_to_public(refreshed)


@router.post("/{order_id}/reorder", response_model=dict)
async def reorder(order_id: int, user: CurrentUser, db: DbDep):
    """Re-add the items of a previous order back into the cart (best-effort)."""
    from sqlalchemy import select

    from app.models import Product, ProductVariant

    order = await _get_my_order(db, order_id, user)
    added = 0
    skipped = 0
    for item in order.items:
        product = await db.get(Product, item.product_id) if item.product_id else None
        if product is None or product.status.value != "active":
            skipped += 1
            continue
        variant = await db.get(ProductVariant, item.variant_id) if item.variant_id else None
        if variant is not None and (variant.product_id != product.id or not variant.is_active):
            variant = None
        available = variant.stock if variant is not None else product.stock
        if available <= 0:
            skipped += 1
            continue
        qty = min(item.quantity, available, 99)

        existing = (
            await db.execute(
                select(CartItem).where(
                    CartItem.user_id == user.id,
                    CartItem.product_id == product.id,
                    CartItem.variant_id == (variant.id if variant else None),
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.quantity = min(existing.quantity + qty, 99, available)
            existing.reminder_sent_at = None
        else:
            db.add(
                CartItem(
                    user_id=user.id,
                    product_id=product.id,
                    variant_id=variant.id if variant else None,
                    quantity=qty,
                )
            )
        added += 1
    await db.commit()

    from app.api.cart import _build_cart

    cart = await _build_cart(db, user.id)
    return {
        "cart": cart.model_dump(mode="json"),
        "added": added,
        "skipped": skipped,
    }
