"""coupons, wishlist, reviews

Revision ID: 0002_features
Revises: 0001_initial
Create Date: 2026-08-04 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_features"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discount_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("discount_type", sa.String(length=8), nullable=False, server_default="percent"),
        sa.Column("value", sa.Numeric(12, 2), nullable=False),
        sa.Column("min_subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("per_user_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_discount_codes_code"),
    )
    op.create_index("ix_discount_codes_code", "discount_codes", ["code"])

    op.create_table(
        "wishlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
    )
    op.create_index("ix_wishlist_items_user_id", "wishlist_items", ["user_id"])
    op.create_index("ix_wishlist_items_product_id", "wishlist_items", ["product_id"])

    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("images", sa.JSON(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "product_id", name="uq_review_user_product"),
    )
    op.create_index("ix_product_reviews_user_id", "product_reviews", ["user_id"])
    op.create_index("ix_product_reviews_product_id", "product_reviews", ["product_id"])

    op.add_column(
        "orders",
        sa.Column(
            "coupon_id",
            sa.Integer(),
            sa.ForeignKey("discount_codes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("orders", sa.Column("coupon_code", sa.String(length=32), nullable=True))
    op.create_index("ix_orders_coupon_id", "orders", ["coupon_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_coupon_id", table_name="orders")
    op.drop_column("orders", "coupon_code")
    op.drop_column("orders", "coupon_id")

    op.drop_index("ix_product_reviews_product_id", table_name="product_reviews")
    op.drop_index("ix_product_reviews_user_id", table_name="product_reviews")
    op.drop_table("product_reviews")

    op.drop_index("ix_wishlist_items_product_id", table_name="wishlist_items")
    op.drop_index("ix_wishlist_items_user_id", table_name="wishlist_items")
    op.drop_table("wishlist_items")

    op.drop_index("ix_discount_codes_code", table_name="discount_codes")
    op.drop_table("discount_codes")
