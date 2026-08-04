import logging

from app.core.telegram import send_telegram_message
from app.models import Order, StoreSettings, User
from app.services.orders import STATUS_LABELS

logger = logging.getLogger(__name__)


def _money(total: float, store: StoreSettings) -> str:
    return f"{store.currency_symbol}{float(total):.2f}"


async def notify_buyer_order_update(order: Order, user: User, store: StoreSettings, message: str | None = None) -> None:
    """Push a Telegram notification to the buyer on order updates. Best-effort."""
    if not user.telegram_id:
        return
    if not (message or order.status):
        return
    text = message or (
        f"Order {order.order_number} is now **{STATUS_LABELS.get(order.status, order.status.value)}**.\n"
        f"Total: {_money(order.total, store)}"
    )
    ok = await send_telegram_message(user.telegram_id, text)
    if not ok:
        logger.info("skip buyer notification for order %s", order.order_number)
