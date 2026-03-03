"""fix submission constraint to include user_id

Revision ID: 005_fix_submission
Revises: 004_verification_requests
"""
from alembic import op
import sqlalchemy as sa

revision = "005_fix_submission"
down_revision = "004_verification_requests"


def upgrade():
    # Drop old constraint
    op.drop_constraint("submissions_assignment_id_key", "submissions", type_="unique")

    # Add user_id column (nullable initially for existing data)
    op.add_column("submissions", sa.Column("user_id", sa.Uuid, nullable=True))

    # Populate user_id from assignments -> courses -> user_id
    # This SQL finds the owner of each assignment and sets it
    op.execute("""
        UPDATE submissions s
        SET user_id = c.user_id
        FROM assignments a
        JOIN courses c ON a.course_id = c.id
        WHERE s.assignment_id = a.id
    """)

    # Make user_id non-nullable
    op.alter_column("submissions", "user_id", nullable=False)

    # Add foreign key
    op.create_foreign_key(
        "submissions_user_id_fkey",
        "submissions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # Add new unique constraint
    op.create_unique_constraint(
        "submissions_user_id_assignment_id_key",
        "submissions",
        ["user_id", "assignment_id"]
    )


def downgrade():
    op.drop_constraint("submissions_user_id_assignment_id_key", "submissions", type_="unique")
    op.drop_constraint("submissions_user_id_fkey", "submissions", type_="foreignkey")
    op.drop_column("submissions", "user_id")
    op.create_unique_constraint("submissions_assignment_id_key", "submissions", ["assignment_id"])
