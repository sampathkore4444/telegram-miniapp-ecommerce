"""Abandoned-cart reminder: best-effort Telegram nudge for stale carts."""
import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.telegram import send_telegram_message
from app.models import CartItem, User

logger = logging.getLogger(__name__)

_MSGS = [
    "Your cart is still waiting for you! {items} ready to order — {link}",
    "Don't forget what's in your bag: {items}. Finish your order here — {link}",
    "Heads up — {items} are still in your cart. Complete your purchase: {link}",
]


async def send_abandoned_cart_reminders(db: AsyncSession, hours: float | None = None) -> int:
    """Send one reminder per user with a cart untouched for `hours`.

    Items are marked `reminder_sent_at` so each user is nudged at most once per
    cart. Returns the number of reminders sent.
    """
    hours = hours if hours is not None else settings.CART_REMINDER_HOURS
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=hours)

    rows = (
        await db.execute(
            select(CartItem).where(CartItem.reminder_sent_at.is_(None))
        )
    ).scalars().all()

    by_user: dict[int, list[CartItem]] = {}
    for item in rows:
        by_user.setdefault(item.user_id, []).append(item)

    sent = 0
    for user_id, items in by_user.items():
        latest = max((i.updated_at or i.created_at or now) for i in items)
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=dt.timezone.utc)
        if latest > cutoff:
            continue
        user = await db.get(User, user_id)
        if user is None or not user.telegram_id:
            for i in items:
                i.reminder_sent_at = now
            continue

        names = []
        seen: set[tuple[int | None, int | None]] = set()
        for i in items:
            key = (i.product_id, i.variant_id)
            if key in seen:
                continue
            seen.add(key)
            label = i.product.name if i.product else "item"
            if i.variant is not None:
                label = f"{label} ({i.variant.name})"
            if i.quantity > 1:
                label = f"{label} × {i.quantity}"
            names.append(label)

        bot = settings.TELEGRAM_BOT_USERNAME or "ShopTrolleyBot"
        link = f"https://t.me/{bot}/{bot}?startapp="
        text = _MSGS[sent % len(_MSGS)].format(
            items=", ".join(names[:3]) + ("…" if len(names) > 3 else ""),
            link=link,
        )
        try:
            ok = await send_telegram_message(user.telegram_id, text)
        except Exception as exc:  # noqa: BLE001 - messaging must never break requests
            logger.warning("cart reminder send error for user %s: %s", user_id, exc)
            ok = False
        if ok:
            for i in items:
                i.reminder_sent_at = now
            sent += 1

    if sent:
        await db.flush()
    return sent
