"""fix pending_visibility_prompt constraint to include user_id

Revision ID: 006_fix_visibility_constraint
Revises: 005_fix_submission
"""
from alembic import op

revision = "006_fix_visibility_constraint"
down_revision = "005_fix_submission"


def upgrade():
    op.drop_constraint(
        "pending_visibility_prompts_course_id_group_id_key",
        "pending_visibility_prompts",
        type_="unique"
    )
    op.create_unique_constraint(
        "pending_visibility_prompts_user_id_course_id_group_id_key",
        "pending_visibility_prompts",
        ["user_id", "course_id", "group_id"]
    )


def downgrade():
    op.drop_constraint(
        "pending_visibility_prompts_user_id_course_id_group_id_key",
        "pending_visibility_prompts",
        type_="unique"
    )
    op.create_unique_constraint(
        "pending_visibility_prompts_course_id_group_id_key",
        "pending_visibility_prompts",
        ["course_id", "group_id"]
    )
