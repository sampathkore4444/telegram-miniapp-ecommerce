"""variants, stock alerts, price tiers, refunds, cart variants, user note

Revision ID: 0003_variants
Revises: 0002_features
Create Date: 2026-08-04 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_variants"
down_revision: Union[str, None] = "0002_features"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Product variants
    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("compare_at_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])

    # Back-in-stock alerts
    op.create_table(
        "stock_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "product_id", "variant_id", name="uq_stock_alert"),
    )
    op.create_index("ix_stock_alerts_user_id", "stock_alerts", ["user_id"])
    op.create_index("ix_stock_alerts_product_id", "stock_alerts", ["product_id"])
    op.create_index("ix_stock_alerts_variant_id", "stock_alerts", ["variant_id"])

    # Quantity-discount tiers on products
    op.add_column("products", sa.Column("price_tiers", sa.JSON(), nullable=True))

    # Cart items: optional variant + reminder timestamp, widened uniqueness
    op.add_column(
        "cart_items",
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True),
    )
    op.add_column("cart_items", sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_cart_items_variant_id", "cart_items", ["variant_id"])
    op.drop_constraint("uq_cart_user_product", "cart_items", type_="unique")
    op.create_unique_constraint("uq_cart_user_product_variant", "cart_items", ["user_id", "product_id", "variant_id"])

    # Orders: refund fields
    op.add_column("orders", sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("orders", sa.Column("refund_reason", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))

    # Order items: variant snapshot
    op.add_column(
        "order_items",
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("order_items", sa.Column("variant_name", sa.String(length=160), nullable=True))

    # Users: admin note
    op.add_column("users", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "note")

    op.drop_column("order_items", "variant_name")
    op.drop_column("order_items", "variant_id")

    op.drop_column("orders", "refunded_at")
    op.drop_column("orders", "refund_reason")
    op.drop_column("orders", "refund_amount")

    op.drop_constraint("uq_cart_user_product_variant", "cart_items", type_="unique")
    op.create_unique_constraint("uq_cart_user_product", "cart_items", ["user_id", "product_id"])
    op.drop_index("ix_cart_items_variant_id", table_name="cart_items")
    op.drop_column("cart_items", "reminder_sent_at")
    op.drop_column("cart_items", "variant_id")

    op.drop_column("products", "price_tiers")

    op.drop_index("ix_stock_alerts_variant_id", table_name="stock_alerts")
    op.drop_index("ix_stock_alerts_product_id", table_name="stock_alerts")
    op.drop_index("ix_stock_alerts_user_id", table_name="stock_alerts")
    op.drop_table("stock_alerts")

    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")
