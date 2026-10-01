"""Persist provider-reported token usage on assessment runs.

Revision ID: 20260929_token_usage
Revises: 20260929_approval_auth_db
"""

import sqlalchemy as sa

from alembic import op

revision = "20260929_token_usage"
down_revision = "20260929_approval_auth_db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_runs",
        sa.Column("token_usage", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("assessment_runs", "token_usage")
