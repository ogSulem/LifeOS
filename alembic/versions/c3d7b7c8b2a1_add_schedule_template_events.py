from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c3d7b7c8b2a1"
down_revision = "b1a5f8c2c9ad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule_template_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("time_from", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_schedule_template_events_user_id", "schedule_template_events", ["user_id"], unique=False)

    op.create_table(
        "habit_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_habit_templates_user_id", "habit_templates", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_habit_templates_user_id", table_name="habit_templates")
    op.drop_table("habit_templates")
    op.drop_index("ix_schedule_template_events_user_id", table_name="schedule_template_events")
    op.drop_table("schedule_template_events")
