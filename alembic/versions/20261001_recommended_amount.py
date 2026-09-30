"""Persist the pipeline-recommended amount for approval enforcement.

Revision ID: 20261001_recommended_amount
Revises: 20260929_token_usage
"""

import sqlalchemy as sa

from alembic import op

revision = "20261001_recommended_amount"
down_revision = "20260929_token_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("recommended_amount", sa.Float()))


def downgrade() -> None:
    op.drop_column("applications", "recommended_amount")
