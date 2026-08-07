"""Resolve which plan a store is on (the plan of its merchant/owner user)."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.plans import Plan, public_features
from app.models import Store


async def get_store_plan(db: AsyncSession, store: Store) -> Plan:
    """A store runs on the plan of its owner. Defaults to Starter."""
    if store.owner is not None:
        return store.owner.plan or Plan.STARTER
    return Plan.STARTER


async def store_plan_payload(db: AsyncSession, store: Store) -> dict:
    """Plan + feature flags for the public store payload."""
    plan = await get_store_plan(db, store)
    return {"plan": plan.value, "features": public_features(plan)}
