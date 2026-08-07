"""Idempotent seed: owner store, store settings, demo categories/products.

Safe to run on every boot; only inserts when rows are missing.
"""
import asyncio
import logging
import re

from sqlalchemy import select

from app.core.config import settings
from app.core.plans import Plan
from app.db.session import AsyncSessionLocal
from app.models import Category, Product, User, UserRole
from app.services.orders import get_store_settings
from app.services.stores import ensure_owner_store

logger = logging.getLogger("seed")

CATEGORIES = [
    {"name": "Electronics", "slug": "electronics", "sort_order": 1},
    {"name": "Fashion", "slug": "fashion", "sort_order": 2},
    {"name": "Home & Living", "slug": "home-living", "sort_order": 3},
    {"name": "Accessories", "slug": "accessories", "sort_order": 4},
]

PRODUCTS = [
    {
        "name": "Wireless Earbuds Pro",
        "category": "electronics",
        "description": "Noise cancelling, 30h battery, IPX5.",
        "price": 49.90,
        "compare_at_price": 69.90,
        "stock": 50,
        "images": [],
    },
    {
        "name": "Smart Watch S9",
        "category": "electronics",
        "description": "AMOLED display, heart-rate & GPS.",
        "price": 129.00,
        "compare_at_price": None,
        "stock": 20,
        "images": [],
    },
    {
        "name": "Cotton Oversized T-Shirt",
        "category": "fashion",
        "description": "100% combed cotton, unisex, 4 sizes.",
        "price": 15.00,
        "compare_at_price": 25.00,
        "stock": 120,
        "images": [],
    },
    {
        "name": "Denim Jacket",
        "category": "fashion",
        "description": "Classic blue denim, medium weight.",
        "price": 55.00,
        "compare_at_price": None,
        "stock": 30,
        "images": [],
    },
    {
        "name": "Ceramic Coffee Mug Set",
        "category": "home-living",
        "description": "Set of 4, dishwasher safe.",
        "price": 22.50,
        "compare_at_price": None,
        "stock": 60,
        "images": [],
    },
    {
        "name": "Memory Foam Pillow",
        "category": "home-living",
        "description": "Cooling gel memory foam, standard size.",
        "price": 35.00,
        "compare_at_price": 45.00,
        "stock": 40,
        "images": [],
    },
    {
        "name": "Leather Phone Case",
        "category": "accessories",
        "description": "Genuine leather, slim fit, wallet slot.",
        "price": 19.90,
        "compare_at_price": None,
        "stock": 200,
        "images": [],
    },
    {
        "name": "Stainless Water Bottle 750ml",
        "category": "accessories",
        "description": "Keeps drinks cold 24h / hot 12h.",
        "price": 18.00,
        "compare_at_price": 24.00,
        "stock": 90,
        "images": [],
    },
]


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "product"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        owner = None
        if settings.admin_ids:
            admin_tg = settings.admin_ids[0]
            owner = (
                await db.execute(select(User).where(User.telegram_id == admin_tg))
            ).scalar_one_or_none()
            if owner is None:
                owner = User(
                    telegram_id=admin_tg,
                    username="owner",
                    first_name="Store",
                    last_name="Owner",
                    role=UserRole.ADMIN,
                    plan=Plan.PRO,
                )
                db.add(owner)
                await db.flush()
            else:
                owner.role = UserRole.ADMIN
                owner.plan = Plan.PRO

        if owner is None:
            owner = (
                await db.execute(
                    select(User).where(User.role == UserRole.ADMIN).order_by(User.id).limit(1)
                )
            ).scalar_one_or_none()
        if owner is None:
            owner = (
                await db.execute(select(User).order_by(User.id).limit(1))
            ).scalar_one_or_none()
        if owner is None:
            logger.warning("no owner available; skipping seed")
            return

        store = await ensure_owner_store(db, owner)
        settings_row = await get_store_settings(db, store.id)
        if not settings_row.store_name or settings_row.store_name == "My Telegram Shop":
            settings_row.store_name = settings.APP_NAME
        if not settings_row.currency_code:
            settings_row.currency_code = "USD"
            settings_row.currency_symbol = "$"
        db.add(settings_row)

        existing_cats = {
            c.slug
            for c in (
                await db.execute(
                    select(Category).where(Category.store_id == store.id)
                )
            ).scalars().all()
        }
        for cat in CATEGORIES:
            if cat["slug"] not in existing_cats:
                db.add(Category(**cat, store_id=store.id))
        await db.flush()

        cats = {
            c.slug: c
            for c in (
                await db.execute(
                    select(Category).where(Category.store_id == store.id)
                )
            ).scalars().all()
        }
        existing_products = {
            p.slug
            for p in (
                await db.execute(
                    select(Product).where(Product.store_id == store.id)
                )
            ).scalars().all()
        }
        for prod in PRODUCTS:
            slug = _slugify(prod["name"])
            if slug in existing_products:
                continue
            data = {k: v for k, v in prod.items() if k != "category"}
            db.add(
                Product(
                    **data,
                    store_id=store.id,
                    category_id=cats[prod["category"]].id if prod["category"] in cats else None,
                    slug=slug,
                    is_featured=slug in {"wireless-earbuds-pro", "cotton-oversized-t-shirt"},
                )
            )
        await db.flush()

        await db.commit()
        logger.info("seed complete")


if __name__ == "__main__":
    asyncio.run(seed())
