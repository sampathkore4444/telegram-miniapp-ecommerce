"""online payments, saved addresses, recently viewed, tracking, broadcast toggles

Revision ID: 0004_features2
Revises: 0003_variants
Create Date: 2026-08-05 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_features2"
down_revision: Union[str, None] = "0003_variants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Online payments: one transaction row per attempt
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gateway", sa.String(length=32), nullable=False),
        sa.Column("provider_ref", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payment_transactions_order_id", "payment_transactions", ["order_id"])
    op.create_index("ix_payment_transactions_provider_ref", "payment_transactions", ["provider_ref"])
    op.create_index("ix_payment_transactions_status", "payment_transactions", ["status"])

    # Saved delivery addresses
    op.create_table(
        "user_addresses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(length=40), nullable=True),
        sa.Column("recipient_name", sa.String(length=120), nullable=False),
        sa.Column("recipient_phone", sa.String(length=32), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_user_addresses_user_id", "user_addresses", ["user_id"])

    # Recently viewed products
    op.create_table(
        "recently_viewed",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "product_id", name="uq_recently_viewed_user_product"),
    )
    op.create_index("ix_recently_viewed_user_id", "recently_viewed", ["user_id"])
    op.create_index("ix_recently_viewed_product_id", "recently_viewed", ["product_id"])
    op.create_index("ix_recently_viewed_viewed_at", "recently_viewed", ["viewed_at"])

    # Orders: tracking/courier fields
    op.add_column("orders", sa.Column("tracking_number", sa.String(length=128), nullable=True))
    op.add_column("orders", sa.Column("tracking_carrier", sa.String(length=64), nullable=True))

    # Store settings: online payments + low-stock alert threshold
    op.add_column(
        "store_settings",
        sa.Column("online_payments_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "store_settings",
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    op.drop_column("store_settings", "low_stock_threshold")
    op.drop_column("store_settings", "online_payments_enabled")

    op.drop_column("orders", "tracking_carrier")
    op.drop_column("orders", "tracking_number")

    op.drop_index("ix_recently_viewed_viewed_at", table_name="recently_viewed")
    op.drop_index("ix_recently_viewed_product_id", table_name="recently_viewed")
    op.drop_index("ix_recently_viewed_user_id", table_name="recently_viewed")
    op.drop_table("recently_viewed")

    op.drop_index("ix_user_addresses_user_id", table_name="user_addresses")
    op.drop_table("user_addresses")

    op.drop_index("ix_payment_transactions_status", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_provider_ref", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_order_id", table_name="payment_transactions")
    op.drop_table("payment_transactions")
