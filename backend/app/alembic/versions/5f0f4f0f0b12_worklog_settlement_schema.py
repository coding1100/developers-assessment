from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "5f0f4f0f0b12"
down_revision = "1a31ce608336"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "worklog",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("settled_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worklog_created_at", "worklog", ["created_at"], unique=False)
    op.create_index("ix_worklog_is_active", "worklog", ["is_active"], unique=False)
    op.create_index("ix_worklog_user_id", "worklog", ["user_id"], unique=False)

    op.create_table(
        "work_segment",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worklog_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("minutes > 0", name="ck_work_segment_minutes_positive"),
        sa.ForeignKeyConstraint(["worklog_id"], ["worklog.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_work_segment_created_at", "work_segment", ["created_at"], unique=False
    )
    op.create_index(
        "ix_work_segment_is_active", "work_segment", ["is_active"], unique=False
    )
    op.create_index(
        "ix_work_segment_worklog_id", "work_segment", ["worklog_id"], unique=False
    )

    op.create_table(
        "work_adjustment",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worklog_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["worklog_id"], ["worklog.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_work_adjustment_created_at",
        "work_adjustment",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_work_adjustment_is_active", "work_adjustment", ["is_active"], unique=False
    )
    op.create_index(
        "ix_work_adjustment_worklog_id",
        "work_adjustment",
        ["worklog_id"],
        unique=False,
    )

    op.create_table(
        "remittance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_remittance_created_at", "remittance", ["created_at"], unique=False
    )
    op.create_index("ix_remittance_period_end", "remittance", ["period_end"], unique=False)
    op.create_index(
        "ix_remittance_period_start", "remittance", ["period_start"], unique=False
    )
    op.create_index("ix_remittance_status", "remittance", ["status"], unique=False)
    op.create_index("ix_remittance_user_id", "remittance", ["user_id"], unique=False)

    op.create_table(
        "remittance_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("remittance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worklog_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["remittance_id"], ["remittance.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worklog_id"], ["worklog.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_remittance_line_created_at", "remittance_line", ["created_at"], unique=False
    )
    op.create_index(
        "ix_remittance_line_remittance_id",
        "remittance_line",
        ["remittance_id"],
        unique=False,
    )
    op.create_index(
        "ix_remittance_line_worklog_id", "remittance_line", ["worklog_id"], unique=False
    )


def downgrade():
    op.drop_index("ix_remittance_line_worklog_id", table_name="remittance_line")
    op.drop_index("ix_remittance_line_remittance_id", table_name="remittance_line")
    op.drop_index("ix_remittance_line_created_at", table_name="remittance_line")
    op.drop_table("remittance_line")

    op.drop_index("ix_remittance_user_id", table_name="remittance")
    op.drop_index("ix_remittance_status", table_name="remittance")
    op.drop_index("ix_remittance_period_start", table_name="remittance")
    op.drop_index("ix_remittance_period_end", table_name="remittance")
    op.drop_index("ix_remittance_created_at", table_name="remittance")
    op.drop_table("remittance")

    op.drop_index("ix_work_adjustment_worklog_id", table_name="work_adjustment")
    op.drop_index("ix_work_adjustment_is_active", table_name="work_adjustment")
    op.drop_index("ix_work_adjustment_created_at", table_name="work_adjustment")
    op.drop_table("work_adjustment")

    op.drop_index("ix_work_segment_worklog_id", table_name="work_segment")
    op.drop_index("ix_work_segment_is_active", table_name="work_segment")
    op.drop_index("ix_work_segment_created_at", table_name="work_segment")
    op.drop_table("work_segment")

    op.drop_index("ix_worklog_user_id", table_name="worklog")
    op.drop_index("ix_worklog_is_active", table_name="worklog")
    op.drop_index("ix_worklog_created_at", table_name="worklog")
    op.drop_table("worklog")
