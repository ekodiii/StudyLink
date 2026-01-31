"""add verification_requests table

Revision ID: 004_verification_requests
Revises: 003_assignment_view
"""
from alembic import op
import sqlalchemy as sa

revision = "004_verification_requests"
down_revision = "003_assignment_view"


def upgrade():
    op.create_table(
        "verification_requests",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("assignment_id", sa.Uuid, sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_id", sa.Uuid, sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requester_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verifier_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("verification_word", sa.String(20), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("assignment_id", "requester_id", "group_id"),
    )


def downgrade():
    op.drop_table("verification_requests")
