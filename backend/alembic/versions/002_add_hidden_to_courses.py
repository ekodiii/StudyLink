"""add hidden to courses

Revision ID: 002
Revises: 001
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"


def upgrade():
    op.add_column("courses", sa.Column("hidden", sa.Boolean(), server_default="false", nullable=False))


def downgrade():
    op.drop_column("courses", "hidden")
