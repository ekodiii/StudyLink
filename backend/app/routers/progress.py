import uuid
from datetime import date, datetime, timezone, timedelta

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
from ..models.verification_request import VerificationRequest, VerificationStatus
from ..schemas.progress import (
    GroupProgressResponse,
    ProgressMember,
    ProgressCourse,
    ProgressAssignment,
    VerificationBrief,
    GroupDashboardResponse,
    DashboardAssignment,
)

router = APIRouter(tags=["progress"])


async def _get_verification_brief(
    db: AsyncSession, assignment_id: uuid.UUID, group_id: uuid.UUID
) -> VerificationBrief | None:
    result = await db.execute(
        select(VerificationRequest).where(
            VerificationRequest.assignment_id == assignment_id,
            VerificationRequest.group_id == group_id,
            VerificationRequest.status.in_([VerificationStatus.pending, VerificationStatus.verified]),
        )
    )
    vr = result.scalar_one_or_none()
    if not vr:
        return None
    requester = (await db.execute(select(User).where(User.id == vr.requester_id))).scalar_one()
    verifier = (await db.execute(select(User).where(User.id == vr.verifier_id))).scalar_one()
    return VerificationBrief(
        id=str(vr.id),
        status=vr.status.value if isinstance(vr.status, VerificationStatus) else vr.status,
        verification_word=vr.verification_word,
        verifier_id=str(vr.verifier_id),
        verifier_username=verifier.username,
        requester_id=str(vr.requester_id),
        requester_username=requester.username,
    )


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
                Course.hidden.is_(False),
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

                verification = await _get_verification_brief(db, assignment.id, group_id)

                progress_assignments.append(ProgressAssignment(
                    assignment_id=str(assignment.id),
                    name=assignment.name,
                    due_at=assignment.due_at,
                    status=sub.status.value if sub else "unsubmitted",
                    submitted_at=sub.submitted_at if sub else None,
                    verification=verification,
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


@router.get("/groups/{group_id}/dashboard", response_model=GroupDashboardResponse)
async def get_group_dashboard(
    group_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mem_check = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id)
    )
    if not mem_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this group")

    now = datetime.now(timezone.utc)
    week_from_now = now + timedelta(days=7)

    members_result = await db.execute(
        select(User).join(GroupMember, GroupMember.user_id == User.id).where(GroupMember.group_id == group_id)
    )

    upcoming = []
    missing = []

    for member_user in members_result.scalars().all():
        courses_result = await db.execute(
            select(Course)
            .join(CourseVisibility, CourseVisibility.course_id == Course.id)
            .where(
                Course.user_id == member_user.id,
                CourseVisibility.group_id == group_id,
                CourseVisibility.visible.is_(True),
                Course.hidden.is_(False),
            )
        )

        for course in courses_result.scalars().all():
            assignments_result = await db.execute(
                select(Assignment).where(Assignment.course_id == course.id)
            )

            for assignment in assignments_result.scalars().all():
                sub_result = await db.execute(
                    select(Submission).where(Submission.assignment_id == assignment.id)
                )
                sub = sub_result.scalar_one_or_none()
                status = sub.status.value if sub else "unsubmitted"

                dash_item = DashboardAssignment(
                    assignment_id=str(assignment.id),
                    name=assignment.name,
                    due_at=assignment.due_at,
                    status=status,
                    course_name=course.course_code or course.name,
                    member_username=member_user.username,
                    member_user_id=str(member_user.id),
                )

                if (
                    assignment.due_at
                    and now <= assignment.due_at <= week_from_now
                    and status in ("unsubmitted", "missing", "late")
                ):
                    upcoming.append(dash_item)

                if status == "missing":
                    missing.append(dash_item)

    upcoming.sort(key=lambda x: x.due_at or datetime.max.replace(tzinfo=timezone.utc))
    missing.sort(key=lambda x: (x.member_username, x.course_name))

    return GroupDashboardResponse(upcoming=upcoming, missing=missing)
