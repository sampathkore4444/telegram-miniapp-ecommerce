from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import AdminStore, DbDep
from app.core.config import settings
from app.core.telegram import send_telegram_message
from app.models import User, UserRole
from app.schemas.broadcast import BroadcastRequest

router = APIRouter(prefix="/admin/broadcasts", tags=["admin"])


@router.post("", response_model=dict)
async def send_broadcast(payload: BroadcastRequest, db: DbDep, store: AdminStore):
    """Send a Telegram message to every active buyer of this store. Best-effort."""
    text = payload.message.strip()
    if not text:
        return {"sent": 0, "total": 0}

    result = await db.execute(
        select(User).where(
            User.role == UserRole.BUYER,
            User.is_active.is_(True),
            User.telegram_id.isnot(None),
        )
    )
    buyers = result.scalars().all()

    sent = 0
    skipped = 0
    for buyer in buyers:
        if not buyer.telegram_id:
            skipped += 1
            continue
        ok = await send_telegram_message(buyer.telegram_id, text)
        if ok:
            sent += 1
        else:
            skipped += 1

    return {
        "sent": sent,
        "skipped": skipped,
        "total": len(buyers),
        "admin_recipients": len(settings.admin_ids),
    }
