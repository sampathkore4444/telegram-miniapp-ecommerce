from fastapi import APIRouter

from app.api.deps import DbDep
from app.core.config import settings
from app.services.orders import get_store_settings

router = APIRouter(prefix="/store", tags=["store"])


@router.get("", response_model=dict)
async def public_store(db: DbDep):
    """Public store configuration used by buyers (currency, delivery, bank info)."""
    store = await get_store_settings(db)
    data = store.to_dict()
    data["telegram_bot_username"] = settings.TELEGRAM_BOT_USERNAME
    return data
