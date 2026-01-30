"""add hidden to courses

Revision ID: 002_add_hidden
Revises: 001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_hidden"
down_revision = "001_initial"


def upgrade():
    op.add_column("courses", sa.Column("hidden", sa.Boolean(), server_default="false", nullable=False))


def downgrade():
    op.drop_column("courses", "hidden")
