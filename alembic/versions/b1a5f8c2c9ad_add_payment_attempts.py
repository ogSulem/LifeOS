from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b1a5f8c2c9ad"
down_revision = "8ce2136d87b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="yookassa"),
        sa.Column("provider_payment_id", sa.String(length=128), nullable=False),
        sa.Column("amount_rub", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_index("ix_payment_attempts_user_id", "payment_attempts", ["user_id"], unique=False)
    op.create_index(
        "ix_payment_attempts_provider_payment_id",
        "payment_attempts",
        ["provider_payment_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_payment_attempts_provider_payment_id", table_name="payment_attempts")
    op.drop_index("ix_payment_attempts_user_id", table_name="payment_attempts")
    op.drop_table("payment_attempts")
