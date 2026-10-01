"""Persist pipeline recommendation for approval gating.

Revision ID: 20261001_recommendation
Revises: 20261001_recommended_amount
"""

import sqlalchemy as sa

from alembic import op

revision = "20261001_recommendation"
down_revision = "20261001_recommended_amount"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("recommendation", sa.String()))


def downgrade() -> None:
    op.drop_column("applications", "recommendation")
