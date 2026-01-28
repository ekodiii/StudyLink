import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.group import Group
from ..models.group_member import GroupMember
from ..models.course import Course
from ..models.assignment import Assignment
from ..models.submission import Submission
from ..models.course_visibility import CourseVisibility
from ..models.institution import Institution
from ..models.user_institution_link import UserInstitutionLink
from ..schemas.progress import (
    GroupProgressResponse,
    ProgressMember,
    ProgressCourse,
    ProgressAssignment,
)

router = APIRouter(tags=["progress"])


@router.get("/groups/{group_id}/progress", response_model=GroupProgressResponse)
async def get_group_progress(
    group_id: uuid.UUID,
    course_filter: uuid.UUID | None = Query(None),
    due_after: date | None = Query(None),
    due_before: date | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify membership
    mem_check = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id)
    )
    if not mem_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this group")

    # Get group
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Get members
    members_result = await db.execute(
        select(User, GroupMember.joined_at)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
    )

    progress_members = []
    for member_user, _ in members_result.all():
        # Get last sync time
        sync_result = await db.execute(
            select(func.max(UserInstitutionLink.last_synced_at))
            .where(UserInstitutionLink.user_id == member_user.id)
        )
        last_synced = sync_result.scalar()

        # Get visible courses for this member in this group
        course_query = (
            select(Course, Institution.name.label("inst_name"))
            .join(CourseVisibility, CourseVisibility.course_id == Course.id)
            .outerjoin(Institution, Institution.id == Course.institution_id)
            .where(
                Course.user_id == member_user.id,
                CourseVisibility.group_id == group_id,
                CourseVisibility.visible.is_(True),
            )
        )
        if course_filter:
            course_query = course_query.where(Course.id == course_filter)

        courses_result = await db.execute(course_query)
        progress_courses = []

        for course, inst_name in courses_result.all():
            # Get assignments
            a_query = select(Assignment).where(Assignment.course_id == course.id)
            if due_after:
                a_query = a_query.where(Assignment.due_at >= due_after)
            if due_before:
                a_query = a_query.where(Assignment.due_at <= due_before)
            a_query = a_query.order_by(Assignment.due_at)

            assignments_result = await db.execute(a_query)
            progress_assignments = []

            for assignment in assignments_result.scalars().all():
                sub_result = await db.execute(
                    select(Submission).where(Submission.assignment_id == assignment.id)
                )
                sub = sub_result.scalar_one_or_none()

                progress_assignments.append(ProgressAssignment(
                    assignment_id=str(assignment.id),
                    name=assignment.name,
                    due_at=assignment.due_at,
                    status=sub.status.value if sub else "unsubmitted",
                    submitted_at=sub.submitted_at if sub else None,
                ))

            progress_courses.append(ProgressCourse(
                course_id=str(course.id),
                name=course.name,
                course_code=course.course_code,
                institution=inst_name,
                assignments=progress_assignments,
            ))

        progress_members.append(ProgressMember(
            user_id=str(member_user.id),
            username=member_user.username,
            discriminator=member_user.discriminator,
            last_synced_at=last_synced,
            courses=progress_courses,
        ))

    return GroupProgressResponse(
        group_id=str(group.id),
        group_name=group.name,
        members=progress_members,
    )
