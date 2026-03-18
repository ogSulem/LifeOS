from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f2a9c8d1e6ab"
down_revision = "e4c1b7a2d9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("trial_used_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "trial_used_at")
