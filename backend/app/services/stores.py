"""Store resolution helpers (active store, primary store, ownership)."""
import datetime as dt
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Store, StoreSettings, User, UserRole


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "shop"


async def _unique_store_slug(
    db: AsyncSession, base: str, exclude_id: int | None = None
) -> str:
    slug = _slugify(base)
    candidate = slug
    counter = 2
    while True:
        stmt = select(Store.id).where(Store.slug == candidate)
        if exclude_id:
            stmt = stmt.where(Store.id != exclude_id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            return candidate
        candidate = f"{slug}-{counter}"
        counter += 1


async def get_store_by_slug(db: AsyncSession, slug: str) -> Store | None:
    result = await db.execute(select(Store).where(Store.slug == slug, Store.is_active.is_(True)))
    return result.scalar_one_or_none()


async def _first_admin(db: AsyncSession) -> User | None:
    result = await db.execute(
        select(User).where(User.role == UserRole.ADMIN).order_by(User.id).limit(1)
    )
    return result.scalar_one_or_none()


async def ensure_owner_store(db: AsyncSession, owner: User) -> Store:
    """Return the owner's primary store, creating one if they have none."""
    result = await db.execute(
        select(Store).where(Store.owner_id == owner.id).order_by(Store.id).limit(1)
    )
    store = result.scalar_one_or_none()
    if store is not None:
        return store
    return await _create_store(db, owner, f"{owner.display_name or 'My'}'s Shop")


async def get_primary_store(db: AsyncSession) -> Store:
    """The deployment-wide fallback store: the first admin's first store.

    Creates it lazily so public endpoints keep working even before the first
    merchant logs in (matches the old singleton behaviour).
    """
    owner = await _first_admin(db)
    if owner is None:
        result = await db.execute(select(User).order_by(User.id).limit(1))
        owner = result.scalar_one_or_none()
    if owner is None:
        raise NotFoundError("No store found", code="no_store")
    return await ensure_owner_store(db, owner)


async def _create_store(
    db: AsyncSession, owner: User, name: str, slug: str | None = None
) -> Store:
    if slug is None:
        slug = await _unique_store_slug(db, name)
    else:
        slug = await _unique_store_slug(db, slug)
    now = dt.datetime.now(dt.timezone.utc)
    store = Store(
        owner_id=owner.id,
        name=name,
        slug=slug,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(store)
    await db.flush()
    settings = StoreSettings(
        store_id=store.id,
        store_name=name,
        currency_code="USD",
        currency_symbol="$",
    )
    db.add(settings)
    await db.flush()
    return store


async def list_owner_stores(db: AsyncSession, owner_id: int) -> list[Store]:
    result = await db.execute(
        select(Store).where(Store.owner_id == owner_id).order_by(Store.id)
    )
    return list(result.scalars().all())
