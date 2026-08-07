from fastapi import APIRouter

from app.api.deps import ActiveStore, DbDep
from app.core.config import settings
from app.core.plans import feature_enabled
from app.services.orders import get_store_settings
from app.services.plans import get_store_plan, store_plan_payload

router = APIRouter(prefix="/store", tags=["store"])


@router.get("", response_model=dict)
async def public_store(db: DbDep, store: ActiveStore):
    """Public store configuration used by buyers (currency, delivery, bank info).

    Also exposes the merchant's ``plan`` + ``features`` so the client can hide
    premium UI, and forces plan-gated payment methods off.
    """
    settings_row = await get_store_settings(db, store.id)
    plan = await get_store_plan(db, store)
    data = settings_row.to_dict()
    data["telegram_bot_username"] = settings.TELEGRAM_BOT_USERNAME
    if not feature_enabled(plan, "online_payments"):
        data["online_payments_enabled"] = False
    data.update(await store_plan_payload(db, store))
    data["store"] = store.to_dict()
    return data
