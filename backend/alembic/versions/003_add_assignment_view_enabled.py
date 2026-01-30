"""add assignment_view_enabled to groups

Revision ID: 003_assignment_view
Revises: 002_add_hidden
"""
from alembic import op
import sqlalchemy as sa

revision = "003_assignment_view"
down_revision = "002_add_hidden"


def upgrade():
    op.add_column("groups", sa.Column("assignment_view_enabled", sa.Boolean(), server_default="true", nullable=False))


def downgrade():
    op.drop_column("groups", "assignment_view_enabled")
