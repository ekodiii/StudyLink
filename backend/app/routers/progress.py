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

    # OPTIMIZED: Get members
    members_result = await db.execute(
        select(User, GroupMember.joined_at)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
    )
    members = members_result.all()
    member_ids = [member_user.id for member_user, _ in members]

    # OPTIMIZED: Get all institution links for all members in one query
    links_result = await db.execute(
        select(UserInstitutionLink)
        .where(UserInstitutionLink.user_id.in_(member_ids))
    )
    # Build lookup: user_id -> [links]
    links_by_user = {}
    for link in links_result.scalars().all():
        if link.user_id not in links_by_user:
            links_by_user[link.user_id] = []
        links_by_user[link.user_id].append(link)

    # OPTIMIZED: Single query to get all visible courses for all members
    course_query = (
        select(Course, Institution.name.label("inst_name"), Course.user_id)
        .join(CourseVisibility, CourseVisibility.course_id == Course.id)
        .outerjoin(Institution, Institution.id == Course.institution_id)
        .where(
            Course.user_id.in_(member_ids),
            CourseVisibility.group_id == group_id,
            CourseVisibility.visible.is_(True),
            Course.hidden.is_(False),
        )
    )
    if course_filter:
        course_query = course_query.where(Course.id == course_filter)

    courses_result = await db.execute(course_query)
    courses_by_user = {}
    for course, inst_name, user_id in courses_result.all():
        if user_id not in courses_by_user:
            courses_by_user[user_id] = []
        courses_by_user[user_id].append((course, inst_name))

    # Get all course IDs
    all_course_ids = [course.id for courses in courses_by_user.values() for course, _ in courses]

    if not all_course_ids:
        # No courses, return empty members
        return GroupProgressResponse(
            group_id=str(group.id),
            group_name=group.name,
            members=[],
        )

    # OPTIMIZED: Single query to get all assignments for all courses
    a_query = select(Assignment).where(Assignment.course_id.in_(all_course_ids))
    if due_after:
        a_query = a_query.where(Assignment.due_at >= due_after)
    if due_before:
        a_query = a_query.where(Assignment.due_at <= due_before)
    a_query = a_query.order_by(Assignment.due_at)

    assignments_result = await db.execute(a_query)
    assignments_by_course = {}
    all_assignment_ids = []
    for assignment in assignments_result.scalars().all():
        if assignment.course_id not in assignments_by_course:
            assignments_by_course[assignment.course_id] = []
        assignments_by_course[assignment.course_id].append(assignment)
        all_assignment_ids.append(assignment.id)

    # OPTIMIZED: Single query to get all submissions
    if all_assignment_ids:
        submissions_result = await db.execute(
            select(Submission).where(Submission.assignment_id.in_(all_assignment_ids))
        )
        submissions_by_assignment = {sub.assignment_id: sub for sub in submissions_result.scalars().all()}
    else:
        submissions_by_assignment = {}

    # OPTIMIZED: Single query to get all verifications
    if all_assignment_ids:
        verifications_result = await db.execute(
            select(VerificationRequest)
            .where(
                VerificationRequest.assignment_id.in_(all_assignment_ids),
                VerificationRequest.group_id == group_id,
                VerificationRequest.status.in_([VerificationStatus.pending, VerificationStatus.verified]),
            )
        )
        verification_requests = verifications_result.scalars().all()

        # Get all unique user IDs from verifications
        vr_user_ids = set()
        for vr in verification_requests:
            vr_user_ids.add(vr.requester_id)
            vr_user_ids.add(vr.verifier_id)

        # Fetch all users involved in verifications in one query
        if vr_user_ids:
            vr_users_result = await db.execute(
                select(User).where(User.id.in_(vr_user_ids))
            )
            vr_users_lookup = {u.id: u for u in vr_users_result.scalars().all()}
        else:
            vr_users_lookup = {}

        # Build verification lookup
        verifications_by_assignment = {}
        for vr in verification_requests:
            requester = vr_users_lookup.get(vr.requester_id)
            verifier = vr_users_lookup.get(vr.verifier_id)

            if requester and verifier:
                verifications_by_assignment[vr.assignment_id] = VerificationBrief(
                    id=str(vr.id),
                    status=vr.status.value if isinstance(vr.status, VerificationStatus) else vr.status,
                    verification_word=vr.verification_word,
                    verifier_id=str(vr.verifier_id),
                    verifier_username=verifier.username,
                    requester_id=str(vr.requester_id),
                    requester_username=requester.username,
                )
    else:
        verifications_by_assignment = {}

    # Build response from cached data
    progress_members = []
    for member_user, _ in members:
        # Get last sync time from links lookup
        last_synced = None
        user_links = links_by_user.get(member_user.id, [])
        if user_links:
            last_synced = max((link.last_synced_at for link in user_links if link.last_synced_at), default=None)

        progress_courses = []
        for course, inst_name in courses_by_user.get(member_user.id, []):
            progress_assignments = []
            for assignment in assignments_by_course.get(course.id, []):
                sub = submissions_by_assignment.get(assignment.id)
                verification = verifications_by_assignment.get(assignment.id)

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
    # Verify membership
    mem_check = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id)
    )
    if not mem_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this group")

    now = datetime.now(timezone.utc)
    week_from_now = now + timedelta(days=7)

    # Get all members
    members_result = await db.execute(
        select(User).join(GroupMember, GroupMember.user_id == User.id).where(GroupMember.group_id == group_id)
    )
    members = members_result.scalars().all()
    member_ids = [m.id for m in members]

    # Single query: all visible courses for all members
    courses_result = await db.execute(
        select(Course)
        .join(CourseVisibility, CourseVisibility.course_id == Course.id)
        .where(
            Course.user_id.in_(member_ids),
            CourseVisibility.group_id == group_id,
            CourseVisibility.visible.is_(True),
            Course.hidden.is_(False),
        )
    )
    courses = courses_result.scalars().all()
    course_ids = [c.id for c in courses]
    courses_by_user = {}
    for course in courses:
        if course.user_id not in courses_by_user:
            courses_by_user[course.user_id] = []
        courses_by_user[course.user_id].append(course)

    if not course_ids:
        return GroupDashboardResponse(upcoming=[], missing=[])

    # Single query: all assignments for all visible courses
    assignments_result = await db.execute(
        select(Assignment).where(Assignment.course_id.in_(course_ids))
    )
    assignments = assignments_result.scalars().all()
    assignment_ids = [a.id for a in assignments]
    assignments_by_course = {}
    for assignment in assignments:
        if assignment.course_id not in assignments_by_course:
            assignments_by_course[assignment.course_id] = []
        assignments_by_course[assignment.course_id].append(assignment)

    # Single query: all submissions
    if assignment_ids:
        submissions_result = await db.execute(
            select(Submission).where(Submission.assignment_id.in_(assignment_ids))
        )
        submissions_by_assignment = {sub.assignment_id: sub for sub in submissions_result.scalars().all()}
    else:
        submissions_by_assignment = {}

    # Build course lookup by ID for names
    course_lookup = {c.id: c for c in courses}

    # Assemble dashboard data
    upcoming = []
    missing = []

    for member_user in members:
        for course in courses_by_user.get(member_user.id, []):
            for assignment in assignments_by_course.get(course.id, []):
                sub = submissions_by_assignment.get(assignment.id)
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

                # Show in upcoming if: due within 7 days AND (not yet submitted OR submitted but not past due)
                if (
                    assignment.due_at
                    and now <= assignment.due_at <= week_from_now
                ):
                    upcoming.append(dash_item)

                if status == "missing":
                    missing.append(dash_item)

    upcoming.sort(key=lambda x: x.due_at or datetime.max.replace(tzinfo=timezone.utc))
    missing.sort(key=lambda x: (x.member_username, x.course_name))

    return GroupDashboardResponse(upcoming=upcoming, missing=missing)
