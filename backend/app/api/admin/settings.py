from fastapi import APIRouter

from app.api.deps import AdminStore, DbDep
from app.core.errors import PermissionError
from app.core.plans import feature_enabled
from app.schemas.settings import SettingsUpdate
from app.services.orders import get_store_settings

router = APIRouter(prefix="/admin/settings", tags=["admin"])


@router.get("", response_model=dict)
async def get_settings(db: DbDep, store: AdminStore):
    settings = await get_store_settings(db, store.id)
    return settings.to_dict()


@router.patch("", response_model=dict)
async def update_settings(payload: SettingsUpdate, db: DbDep, store: AdminStore):
    settings = await get_store_settings(db, store.id)
    data = payload.model_dump(exclude_unset=True)
    if (
        data.get("online_payments_enabled")
        and not feature_enabled(store.owner.plan, "online_payments")
    ):
        raise PermissionError(
            "Online payments are not available on your current plan.", code="plan_required"
        )
    for key, value in data.items():
        setattr(settings, key, value)
    await db.commit()
    await db.refresh(settings)
    return settings.to_dict()
