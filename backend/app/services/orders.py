import datetime as dt
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError, NotFoundError
from app.core.plans import feature_enabled
from app.models import (
    CartItem,
    DiscountCode,
    DiscountType,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusLog,
    PaymentMethod,
    PaymentStatus,
    Product,
    ProductVariant,
    StoreSettings,
    User,
)
from app.schemas.order import CheckoutRequest
from app.services.pricing import line_subtotal, unit_price_for
from app.services.stock_alerts import alert_admin_low_stock

TERMINAL_STATUSES = {
    OrderStatus.COMPLETED,
    OrderStatus.REFUNDED,
    OrderStatus.CANCELLED,
    OrderStatus.REJECTED,
}

# Which order statuses allow each payment_status value.
PAYMENT_STATUS_BY_ORDER_STATUS = {
    OrderStatus.PENDING: PaymentStatus.UNPAID,
    OrderStatus.PENDING_PAYMENT: PaymentStatus.UNPAID,
    OrderStatus.UNDER_REVIEW: PaymentStatus.UNDER_REVIEW,
    OrderStatus.CONFIRMED: PaymentStatus.PAID,
    OrderStatus.PROCESSING: PaymentStatus.PAID,
    OrderStatus.SHIPPED: PaymentStatus.PAID,
    OrderStatus.DELIVERED: PaymentStatus.PAID,
    OrderStatus.COMPLETED: PaymentStatus.PAID,
    OrderStatus.REFUNDED: PaymentStatus.REFUNDED,
    OrderStatus.CANCELLED: PaymentStatus.UNPAID,
    OrderStatus.REJECTED: PaymentStatus.REJECTED,
}

STATUS_LABELS = {
    OrderStatus.PENDING: "Pending",
    OrderStatus.PENDING_PAYMENT: "Awaiting payment",
    OrderStatus.UNDER_REVIEW: "Payment under review",
    OrderStatus.CONFIRMED: "Confirmed",
    OrderStatus.PROCESSING: "Processing",
    OrderStatus.SHIPPED: "Shipped",
    OrderStatus.DELIVERED: "Delivered",
    OrderStatus.COMPLETED: "Completed",
    OrderStatus.REFUNDED: "Refunded",
    OrderStatus.CANCELLED: "Cancelled",
    OrderStatus.REJECTED: "Rejected",
}

# Allowed transitions, keyed by current status. None = only buyer-cancel/reject handled separately.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.PENDING_PAYMENT: {OrderStatus.CANCELLED, OrderStatus.CONFIRMED, OrderStatus.REJECTED},
    OrderStatus.UNDER_REVIEW: {OrderStatus.CONFIRMED, OrderStatus.REJECTED},
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.REFUNDED: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.REJECTED: set(),
}


async def get_store_settings(db: AsyncSession, store_id: int | None = None) -> StoreSettings:
    if store_id is None:
        from app.services.stores import get_primary_store

        store = await get_primary_store(db)
        store_id = store.id
    result = await db.execute(
        select(StoreSettings).where(StoreSettings.store_id == store_id)
    )
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        settings_row = StoreSettings(store_id=store_id)
        db.add(settings_row)
        await db.flush()
    return settings_row


async def compute_totals(
    db: AsyncSession,
    items: list[tuple[Product, ProductVariant | None, int]],
    coupon: DiscountCode | None = None,
    store_id: int | None = None,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Returns (subtotal, delivery_fee, discount, total). All from server-side prices."""
    subtotal = sum((line_subtotal(p, v, qty) for p, v, qty in items), Decimal("0"))
    store = await get_store_settings(db, store_id)
    delivery_fee = Decimal(str(store.delivery_fee or 0))
    threshold = store.free_delivery_threshold
    if threshold is not None and subtotal >= Decimal(str(threshold)):
        delivery_fee = Decimal("0")

    discount = Decimal("0")
    if coupon is not None:
        if coupon.discount_type == DiscountType.PERCENT:
            discount = (subtotal * Decimal(str(coupon.value))) / Decimal("100")
        else:
            discount = min(Decimal(str(coupon.value)), subtotal)
        discount = min(discount, subtotal)

    total = subtotal + delivery_fee - discount
    return subtotal, delivery_fee, discount, total


async def validate_coupon(
    db: AsyncSession,
    code: str,
    user: User,
    subtotal: Decimal | None = None,
    store_id: int | None = None,
) -> DiscountCode:
    """Validate a coupon code for a user/order. Raises AppError with a stable code."""
    normalized = (code or "").strip().upper()
    if not normalized:
        raise AppError("Please enter a coupon code.", code="coupon_required")
    stmt = select(DiscountCode).where(DiscountCode.code == normalized)
    if store_id is not None:
        stmt = stmt.where(DiscountCode.store_id == store_id)
    result = await db.execute(stmt)
    coupon = result.scalar_one_or_none()
    if coupon is None:
        raise AppError("Invalid coupon code.", code="coupon_not_found")
    if not coupon.is_active:
        raise AppError("This coupon is no longer active.", code="coupon_inactive")

    now = dt.datetime.now(dt.timezone.utc)
    if coupon.active_from is not None and coupon.active_from > now:
        raise AppError("This coupon is not active yet.", code="coupon_not_started")
    if coupon.active_until is not None and coupon.active_until < now:
        raise AppError("This coupon has expired.", code="coupon_expired")
    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        raise AppError("This coupon has reached its usage limit.", code="coupon_used_up")
    if subtotal is not None and subtotal < coupon.min_subtotal:
        raise AppError(
            f"Minimum order total for this coupon is {coupon.min_subtotal:.2f}.",
            code="coupon_min_subtotal",
        )

    used_by_user = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.user_id == user.id, Order.coupon_id == coupon.id
            )
        )
    ).scalar() or 0
    if used_by_user >= coupon.per_user_limit:
        raise AppError("You have already used this coupon.", code="coupon_used_by_user")
    return coupon


async def _log_status(db: AsyncSession, order: Order, to_status: OrderStatus, note: str | None, actor_id: int | None) -> None:
    entry = OrderStatusLog(
        order_id=order.id,
        from_status=order.status.value if order.status else None,
        to_status=to_status.value,
        note=note,
        actor_id=actor_id,
    )
    db.add(entry)
    order.status = to_status
    order.payment_status = PAYMENT_STATUS_BY_ORDER_STATUS[to_status]


async def change_order_status(
    db: AsyncSession,
    order: Order,
    to_status: OrderStatus,
    actor_id: int,
    note: str | None = None,
) -> Order:
    """Apply a status transition with validation, stock side-effects and a log entry."""
    current = order.status
    if current in TERMINAL_STATUSES:
        raise AppError(f"Order is already {current.value}; it cannot be changed.", code="order_terminal")
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if to_status not in allowed:
        raise AppError(
            f"Cannot move order from '{current.value}' to '{to_status.value}'.",
            code="invalid_transition",
        )

    if to_status in {OrderStatus.CANCELLED, OrderStatus.REJECTED}:
        await _restock_items(db, order)
        if to_status == OrderStatus.CANCELLED:
            order.cancel_reason = note or "Cancelled by shop"
            note = note or "Cancelled by shop"
        elif to_status == OrderStatus.REJECTED:
            order.payment_status = PaymentStatus.REJECTED

    await _log_status(db, order, to_status, note, actor_id)
    await db.flush()
    return order


async def _restock_items(db: AsyncSession, order: Order) -> None:
    for item in order.items:
        if item.variant_id:
            variant = await db.get(ProductVariant, item.variant_id)
            if variant:
                variant.stock += item.quantity
        elif item.product_id:
            product = await db.get(Product, item.product_id)
            if product:
                product.stock += item.quantity


async def decrement_stock(db: AsyncSession, items: list[tuple[Product, ProductVariant | None, int]]) -> None:
    for product, variant, qty in items:
        if variant is not None:
            variant.stock -= qty
            product.sold_count += qty
        else:
            product.stock -= qty
            product.sold_count += qty


async def create_order(
    db: AsyncSession,
    user: User,
    payload: CheckoutRequest,
    cart_items: list[CartItem],
    store_id: int | None = None,
) -> Order:
    from app.models import Store

    if store_id is None:
        from app.services.stores import get_primary_store

        store = await get_primary_store(db)
        store_id = store.id
    store = await get_store_settings(db, store_id)
    from app.services.plans import get_store_plan

    store_obj = await db.get(Store, store_id)
    plan = await get_store_plan(db, store_obj)
    if payload.payment_method == PaymentMethod.BANK_QR and not store.bank_qr_enabled:
        raise AppError("Bank QR payments are currently disabled.", code="payment_disabled")
    if payload.payment_method == PaymentMethod.COD and not store.cod_enabled:
        raise AppError("Cash on delivery is currently disabled.", code="payment_disabled")
    if payload.payment_method == PaymentMethod.ONLINE and not store.online_payments_enabled:
        raise AppError("Online payments are currently disabled.", code="payment_disabled")
    if payload.payment_method == PaymentMethod.ONLINE and not feature_enabled(plan, "online_payments"):
        raise AppError(
            "Online payments are not available on this store's plan.", code="plan_required"
        )

    products: list[tuple[Product, ProductVariant | None, int]] = []
    for item in cart_items:
        product = item.product
        variant = item.variant
        if product.status.value != "active":
            raise AppError(f"'{product.name}' is no longer available.", code="product_unavailable")
        available = variant.stock if variant is not None else product.stock
        if available < item.quantity:
            unit_label = f" ({variant.name})" if variant is not None else ""
            raise AppError(
                f"Only {available} unit(s) of '{product.name}{unit_label}' left in stock.",
                code="insufficient_stock",
            )
        products.append((product, variant, item.quantity))

    subtotal_raw = sum((line_subtotal(p, v, qty) for p, v, qty in products), Decimal("0"))
    coupon = None
    if payload.coupon_code:
        if not feature_enabled(plan, "coupons"):
            raise AppError(
                "Coupons are not enabled on this store's plan.", code="plan_required"
            )
        coupon = await validate_coupon(
            db, payload.coupon_code, user, subtotal=subtotal_raw, store_id=store_id
        )

    subtotal, delivery_fee, discount, total = await compute_totals(
        db, products, coupon, store_id=store_id
    )
    now = dt.datetime.now(dt.timezone.utc)

    order = Order(
        user_id=user.id,
        store_id=store_id,
        status=(
            OrderStatus.PENDING
            if payload.payment_method == PaymentMethod.COD
            else OrderStatus.PENDING_PAYMENT
        ),
        payment_method=payload.payment_method,
        payment_status=(
            PaymentStatus.UNPAID
        ),
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount=discount,
        total=total,
        recipient_name=payload.recipient_name,
        recipient_phone=payload.recipient_phone,
        delivery_address=payload.delivery_address,
        delivery_note=payload.delivery_note,
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    await db.flush()

    if coupon:
        coupon.used_count += 1
        order.coupon_id = coupon.id
        order.coupon_code = coupon.code

    for product, variant, qty in products:
        unit = unit_price_for(product, variant, qty)
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                variant_id=variant.id if variant else None,
                product_name=product.name,
                variant_name=variant.name if variant else None,
                image_url=(product.images or [None])[0],
                unit_price=unit,
                quantity=qty,
                total=unit * qty,
            )
        )

    await _log_status(db, order, order.status, "Order placed", user.id)
    stock_before = [
        (product, variant, variant.stock if variant is not None else product.stock)
        for product, variant, _ in products
    ]
    await decrement_stock(db, products)
    threshold = getattr(store, "low_stock_threshold", 5) or 5
    for product, variant, before in stock_before:
        after = variant.stock if variant is not None else product.stock
        await alert_admin_low_stock(db, product, threshold, before, after, variant=variant)
    await db.flush()
    return order


async def get_order_or_404(
    db: AsyncSession, order_id: int, user: User | None = None, store_id: int | None = None
) -> Order:
    stmt = select(Order).options(
        selectinload(Order.items),
        selectinload(Order.status_logs),
    ).where(Order.id == order_id)
    if user is not None and not user.is_admin:
        stmt = stmt.where(Order.user_id == user.id)
    if store_id is not None:
        stmt = stmt.where(Order.store_id == store_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Order not found")
    return order


async def submit_payment_proof(
    db: AsyncSession,
    order: Order,
    actor: User,
    transaction_ref: str,
    receipt_image: str | None,
) -> Order:
    """Buyer submits (or re-submits) a bank-QR payment proof."""
    if order.payment_method != PaymentMethod.BANK_QR:
        raise AppError("This order does not require bank QR payment.", code="not_bank_qr")
    if order.status not in {OrderStatus.PENDING_PAYMENT, OrderStatus.REJECTED}:
        raise AppError(
            "Payment proof can only be submitted for pending orders.",
            code="invalid_order_state",
        )

    previous = order.status
    order.receipt_image = receipt_image
    order.transaction_ref = transaction_ref
    order.status = OrderStatus.UNDER_REVIEW
    order.payment_status = PaymentStatus.UNDER_REVIEW
    db.add(
        OrderStatusLog(
            order_id=order.id,
            from_status=previous.value if previous else None,
            to_status=OrderStatus.UNDER_REVIEW.value,
            note=f"Payment proof submitted (ref: {transaction_ref})",
            actor_id=actor.id,
        )
    )
    await db.flush()
    return order


async def refund_order(
    db: AsyncSession,
    order: Order,
    amount: Decimal,
    reason: str,
    actor_id: int,
) -> Order:
    """Refund a (paid) order. Marks the order refunded and records the refund."""
    if order.status in TERMINAL_STATUSES:
        raise AppError(
            f"Order is already {order.status.value}; it cannot be refunded.",
            code="order_terminal",
        )
    if amount > Decimal(order.total):
        raise AppError(
            "Refund amount cannot exceed the order total.", code="invalid_refund_amount"
        )

    now = dt.datetime.now(dt.timezone.utc)
    order.refund_amount = amount
    order.refund_reason = reason or "Refund"
    order.refunded_at = now
    await _log_status(db, order, OrderStatus.REFUNDED, reason or "Refunded", actor_id)
    await db.flush()
    return order
