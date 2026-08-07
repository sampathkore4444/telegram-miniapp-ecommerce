import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.models import (
    Order,
    OrderStatus,
    PaymentMethod,
    PaymentTransaction,
    StoreSettings,
    User,
)
from app.schemas.payment import PayResult
from app.services.orders import change_order_status, get_store_settings
from app.services.payments import get_gateway


async def _pending_transaction(
    db: AsyncSession, order: Order, provider_ref: str | None = None
) -> PaymentTransaction | None:
    stmt = select(PaymentTransaction).where(
        PaymentTransaction.order_id == order.id,
        PaymentTransaction.status == "pending",
    )
    if provider_ref:
        stmt = stmt.where(PaymentTransaction.provider_ref == provider_ref)
    return (await db.execute(stmt)).scalar_one_or_none()


async def init_payment(db: AsyncSession, order: Order, user: User) -> PayResult:
    """Create (or reuse) a payment intent for an online-payment order."""
    if order.payment_method != PaymentMethod.ONLINE:
        raise AppError("This order does not use online payment.", code="not_online_payment")
    if order.status not in {OrderStatus.PENDING_PAYMENT, OrderStatus.REJECTED}:
        raise AppError(
            "This order is not awaiting payment.", code="invalid_order_state"
        )

    store = await get_store_settings(db, order.store_id)
    existing = await _pending_transaction(db, order)
    if existing is not None:
        return PayResult(
            order_id=order.id,
            gateway=existing.gateway,
            provider_ref=existing.provider_ref,
            payment_url=f"#/pay/order/{order.id}?tx={existing.provider_ref}",
            amount=float(existing.amount),
            currency=existing.currency,
            status=existing.status,
        )

    gateway = get_gateway()
    intent = await gateway.create_intent(order, store)
    tx = PaymentTransaction(
        order_id=order.id,
        gateway=gateway.name,
        provider_ref=intent.provider_ref,
        status="pending",
        amount=order.total,
        currency=store.currency_code or "USD",
    )
    db.add(tx)
    await db.flush()
    return PayResult(
        order_id=order.id,
        gateway=gateway.name,
        provider_ref=intent.provider_ref,
        payment_url=intent.payment_url,
        amount=float(order.total),
        currency=tx.currency,
        status="pending",
    )


async def settle_payment(
    db: AsyncSession,
    order: Order,
    user: User,
    provider_ref: str,
    approved: bool,
) -> Order:
    """Resolve a pending intent via the gateway and update the order."""
    stmt = select(PaymentTransaction).where(
        PaymentTransaction.order_id == order.id,
        PaymentTransaction.provider_ref == provider_ref,
    )
    tx = (await db.execute(stmt)).scalar_one_or_none()
    if tx is None:
        raise NotFoundError("Payment intent not found")
    if tx.status != "pending":
        raise AppError("This payment was already resolved.", code="payment_already_resolved")
    if order.status not in {OrderStatus.PENDING_PAYMENT, OrderStatus.REJECTED}:
        raise AppError(
            "This order is not awaiting payment.", code="invalid_order_state"
        )

    store = await get_store_settings(db, order.store_id)
    gateway = get_gateway(tx.gateway)
    success, message = await gateway.confirm_intent(order, store, tx.provider_ref, approved)

    now = dt.datetime.now(dt.timezone.utc)
    tx.message = message
    if success:
        order = await change_order_status(
            db, order, OrderStatus.CONFIRMED, user.id, note="Online payment approved"
        )
        order.paid_at = now
        tx.status = "succeeded"
        tx.paid_at = now
    else:
        order = await change_order_status(
            db, order, OrderStatus.REJECTED, user.id, note="Online payment declined"
        )
        tx.status = "failed"
    await db.flush()
    return order
