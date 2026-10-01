"""Create approval workflow records.

Revision ID: 20260929_approval_auth_db
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "20260929_approval_auth_db"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("authority_limit", sa.Float(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_amount", sa.Float(), nullable=False),
        sa.Column("tenure_months", sa.Integer(), nullable=False),
        sa.Column("monthly_income", sa.Float(), nullable=False),
        sa.Column("other_monthly_installments", sa.Float(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("application_date", sa.Date(), nullable=False),
        sa.Column("policy_edition", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("decision_reason", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "assessment_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "application_id",
            sa.String(),
            sa.ForeignKey("applications.id"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("policy_edition", sa.String(), nullable=False),
        sa.Column("steps_executed", sa.JSON(), nullable=False),
        sa.Column("chunk_ids", sa.JSON(), nullable=False),
        sa.Column("removed_fields", sa.JSON(), nullable=False),
        sa.Column("tokens_consumed", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "approval_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "application_id",
            sa.String(),
            sa.ForeignKey("applications.id"),
            nullable=False,
        ),
        sa.Column(
            "approver_id", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("amount", sa.Float()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("approval_records")
    op.drop_table("assessment_runs")
    op.drop_table("applications")
    op.drop_table("users")
