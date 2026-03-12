from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e4c1b7a2d9f0"
down_revision = "d7b2f1a0c9e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule_template_applied_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "day", name="uq_schedule_template_applied_day"),
    )
    op.create_index(
        "ix_schedule_template_applied_days_user_id",
        "schedule_template_applied_days",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_schedule_template_applied_days_day",
        "schedule_template_applied_days",
        ["day"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_template_applied_days_day", table_name="schedule_template_applied_days")
    op.drop_index("ix_schedule_template_applied_days_user_id", table_name="schedule_template_applied_days")
    op.drop_table("schedule_template_applied_days")
