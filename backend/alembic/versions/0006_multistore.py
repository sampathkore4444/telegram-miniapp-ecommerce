"""multi-store: stores table, per-store scoping of tenant tables

Adds a `stores` table owned by merchant admins and threads `store_id` through
every tenant table (products, categories, discount_codes, orders, cart_items,
wishlist_items, product_reviews, stock_alerts, recently_viewed, store_settings).
Existing rows are backfilled into a single default store created for the first
admin (falling back to the first user).

Revision ID: 0006_multistore
Revises: 0005_plans
Create Date: 2026-08-07 00:00:00

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_multistore"
down_revision: Union[str, None] = "0005_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = [
    "products",
    "categories",
    "discount_codes",
    "orders",
    "cart_items",
    "wishlist_items",
    "product_reviews",
    "stock_alerts",
    "recently_viewed",
    "store_settings",
]

# store_settings.store_id gets a UNIQUE index (one settings row per store).
UNIQUE_STORE_ID_TABLES = {"store_settings"}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "shop"


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slug", name="uq_stores_slug"),
    )
    op.create_index("ix_stores_owner_id", "stores", ["owner_id"])
    op.create_index("ix_stores_slug", "stores", ["slug"])

    # Backfill: create one default store owned by the first admin (or user).
    # users.role is stored via Enum(UserRole, native_enum=False) as 'ADMIN' but
    # older rows may use the lowercase server default, so match case-insensitively.
    owner = bind.execute(
        sa.text(
            "SELECT id, COALESCE(NULLIF(username, ''), 'My Shop') "
            "FROM users WHERE LOWER(role) = 'admin' ORDER BY id LIMIT 1"
        )
    ).first()
    if owner is None:
        owner = bind.execute(
            sa.text(
                "SELECT id, COALESCE(NULLIF(username, ''), 'My Shop') "
                "FROM users ORDER BY id LIMIT 1"
            )
        ).first()

    store_id = None
    if owner is not None:
        owner_id, base_name = owner
        name = base_name or "My Shop"
        slug = _slugify(name)
        candidate = slug
        counter = 2
        while True:
            existing = bind.execute(
                sa.text("SELECT id FROM stores WHERE slug = :s"), {"s": candidate}
            ).scalar()
            if existing is None:
                break
            candidate = f"{slug}-{counter}"
            counter += 1

        bind.execute(
            sa.text(
                "INSERT INTO stores (owner_id, name, slug, is_active, created_at, updated_at) "
                "VALUES (:o, :n, :s, true, now(), now())"
            ),
            {"o": owner_id, "n": name, "s": candidate},
        )
        store_id = bind.execute(
            sa.text("SELECT id FROM stores ORDER BY id DESC LIMIT 1")
        ).scalar()

    for table in TENANT_TABLES:
        op.add_column(
            table,
            sa.Column(
                "store_id",
                sa.Integer(),
                sa.ForeignKey("stores.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        if store_id is not None:
            bind.execute(
                sa.text(f"UPDATE {table} SET store_id = :sid"), {"sid": store_id}
            )
        # Empty tables have no rows to backfill, so NOT NULL is always safe.
        op.alter_column(table, "store_id", nullable=False)
        if table in UNIQUE_STORE_ID_TABLES:
            op.create_index(f"ix_{table}_store_id", table, ["store_id"], unique=True)
        else:
            op.create_index(f"ix_{table}_store_id", table, ["store_id"])

    # Per-store uniqueness replaces the old global-unique constraints.
    op.drop_constraint("uq_products_slug", "products", type_="unique")
    op.create_unique_constraint("uq_products_store_slug", "products", ["store_id", "slug"])

    op.drop_constraint("uq_categories_slug", "categories", type_="unique")
    op.create_unique_constraint("uq_categories_store_slug", "categories", ["store_id", "slug"])

    op.drop_constraint("uq_discount_codes_code", "discount_codes", type_="unique")
    op.create_unique_constraint(
        "uq_discount_codes_store_code", "discount_codes", ["store_id", "code"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_discount_codes_store_code", "discount_codes", type_="unique")
    op.create_unique_constraint("uq_discount_codes_code", "discount_codes", ["code"])

    op.drop_constraint("uq_categories_store_slug", "categories", type_="unique")
    op.create_unique_constraint("uq_categories_slug", "categories", ["slug"])

    op.drop_constraint("uq_products_store_slug", "products", type_="unique")
    op.create_unique_constraint("uq_products_slug", "products", ["slug"])

    for table in TENANT_TABLES:
        op.drop_index(f"ix_{table}_store_id", table_name=table)
        op.drop_column(table, "store_id")

    op.drop_index("ix_stores_slug", table_name="stores")
    op.drop_index("ix_stores_owner_id", table_name="stores")
    op.drop_table("stores")
