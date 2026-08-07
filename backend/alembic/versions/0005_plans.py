"""merchant plan column (Starter / Growth / Pro)

Revision ID: 0005_plans
Revises: 0004_features2
Create Date: 2026-08-07 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_plans"
down_revision: Union[str, None] = "0004_features2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("plan", sa.String(length=16), nullable=False, server_default="starter"),
    )
    op.create_index("ix_users_plan", "users", ["plan"])


def downgrade() -> None:
    op.drop_index("ix_users_plan", table_name="users")
    op.drop_column("users", "plan")
