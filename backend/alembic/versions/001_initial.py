"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-01-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("discriminator", sa.String(4), nullable=False),
        sa.Column("apple_id", sa.String(255), unique=True),
        sa.Column("google_id", sa.String(255), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("username", "discriminator"),
    )

    op.create_table(
        "institutions",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canvas_domain", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("invite_code", sa.String(8), unique=True, nullable=False),
        sa.Column("leader_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_institution_links",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("institution_id", sa.Uuid, sa.ForeignKey("institutions.id")),
        sa.Column("canvas_user_id", sa.String(255)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "institution_id"),
    )

    op.create_table(
        "group_members",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", sa.Uuid, sa.ForeignKey("groups.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("group_id", "user_id"),
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("institution_id", sa.Uuid, sa.ForeignKey("institutions.id")),
        sa.Column("canvas_course_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("course_code", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "canvas_course_id"),
    )

    op.create_table(
        "assignments",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id", sa.Uuid, sa.ForeignKey("courses.id", ondelete="CASCADE")),
        sa.Column("canvas_assignment_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("points_possible", sa.Numeric(10, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "canvas_assignment_id"),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("assignment_id", sa.Uuid, sa.ForeignKey("assignments.id", ondelete="CASCADE"), unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="unsubmitted"),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "course_visibility",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id", sa.Uuid, sa.ForeignKey("courses.id", ondelete="CASCADE")),
        sa.Column("group_id", sa.Uuid, sa.ForeignKey("groups.id", ondelete="CASCADE")),
        sa.Column("visible", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("course_id", "group_id"),
    )

    op.create_table(
        "pending_visibility_prompts",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("course_id", sa.Uuid, sa.ForeignKey("courses.id", ondelete="CASCADE")),
        sa.Column("group_id", sa.Uuid, sa.ForeignKey("groups.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "group_id"),
    )


def downgrade() -> None:
    op.drop_table("pending_visibility_prompts")
    op.drop_table("course_visibility")
    op.drop_table("submissions")
    op.drop_table("assignments")
    op.drop_table("courses")
    op.drop_table("group_members")
    op.drop_table("user_institution_links")
    op.drop_table("groups")
    op.drop_table("institutions")
    op.drop_table("users")
