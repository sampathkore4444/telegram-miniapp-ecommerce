from fastapi import APIRouter

from app.api.deps import CurrentAdmin, DbDep
from app.models import StoreSettings
from app.schemas.settings import SettingsUpdate
from app.services.orders import get_store_settings

router = APIRouter(prefix="/admin/settings", tags=["admin"])


@router.get("", response_model=dict)
async def get_settings(db: DbDep, admin: CurrentAdmin):
    store = await get_store_settings(db)
    return store.to_dict()


@router.patch("", response_model=dict)
async def update_settings(payload: SettingsUpdate, db: DbDep, admin: CurrentAdmin):
    store = await get_store_settings(db)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(store, key, value)
    await db.commit()
    await db.refresh(store)
    return store.to_dict()
