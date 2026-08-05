import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.telegram import notify_admins, send_telegram_message
from app.models import Product, ProductVariant, StockAlert, User

logger = logging.getLogger(__name__)


async def alert_admin_low_stock(
    db: AsyncSession,
    product: Product,
    threshold: int,
    before: int,
    after: int,
    variant: ProductVariant | None = None,
) -> bool:
    """Notify admins on low-stock / out-of-stock / back-in-stock transitions.

    Only fires when the stock actually crosses a boundary, so it will not spam
    admins on every edit. Returns True when a message was sent. Best-effort.
    """
    unit_label = f" ({variant.name})" if variant is not None else ""
    label = f"**{product.name}{unit_label}**"
    if before > 0 and after == 0:
        text = f"⚠️ Out of stock: {label} is now out of stock."
    elif before > threshold >= after > 0:
        text = f"⚠️ Low stock: only **{after}** left of {label} (threshold: {threshold})."
    elif before <= threshold and after > threshold:
        text = f"✅ Back in stock: {label} is stocked again ({after} units)."
    else:
        return False
    try:
        return await notify_admins(text) > 0
    except Exception as exc:  # noqa: BLE001 - alerts must never break requests
        logger.warning("admin low-stock alert error: %s", exc)
        return False


async def alert_admin_product_created_low_stock(
    product: Product, threshold: int
) -> bool:
    """Warn admins when a brand-new product starts at/below the low-stock threshold."""
    if not (0 < product.stock <= threshold):
        return False
    text = (
        f"⚠️ Low stock: new product **{product.name}** starts with only "
        f"**{product.stock}** units (threshold: {threshold})."
    )
    try:
        return await notify_admins(text) > 0
    except Exception as exc:  # noqa: BLE001
        logger.warning("admin new-product low-stock alert error: %s", exc)
        return False


async def trigger_stock_alerts(
    db: AsyncSession,
    product: Product,
    variant: ProductVariant | None = None,
) -> int:
    """Notify buyers who asked to be alerted when `product`/`variant` is back in stock.

    Returns the number of notifications sent. Best-effort (never raises).
    """
    stmt = select(StockAlert).where(
        StockAlert.product_id == product.id,
        StockAlert.is_notified.is_(False),
    )
    if variant is not None:
        stmt = stmt.where(StockAlert.variant_id == variant.id)
    else:
        stmt = stmt.where(StockAlert.variant_id.is_(None))

    alerts = (await db.execute(stmt)).scalars().all()
    if not alerts:
        return 0

    unit_label = f" ({variant.name})" if variant is not None else ""
    bot = settings.TELEGRAM_BOT_USERNAME or "ShopTrolleyBot"
    link = f"https://t.me/{bot}/{bot}?startapp=product_{product.id}"
    text = (
        f"Good news — **{product.name}{unit_label}** is back in stock!\n"
        f"Order it now: {link}"
    )

    sent = 0
    for alert in alerts:
        user = await db.get(User, alert.user_id)
        if user is None or not user.telegram_id:
            alert.is_notified = True
            sent += 1
            continue
        try:
            ok = await send_telegram_message(user.telegram_id, text)
        except Exception as exc:  # noqa: BLE001 - messaging must never break requests
            logger.warning("stock alert send error for user %s: %s", alert.user_id, exc)
            ok = False
        if ok:
            alert.is_notified = True
            sent += 1
    await db.flush()
    return sent
