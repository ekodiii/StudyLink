from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.institution import Institution
from ..models.user_institution_link import UserInstitutionLink
from ..models.course import Course
from ..models.assignment import Assignment
from ..models.submission import Submission, SubmissionStatus
from ..models.group_member import GroupMember
from ..models.course_visibility import CourseVisibility
from ..models.pending_visibility_prompt import PendingVisibilityPrompt
from ..schemas.sync import SyncRequest, SyncResponse

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncResponse)
async def sync_data(
    req: SyncRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    # Upsert institution
    inst_result = await db.execute(
        select(Institution).where(Institution.canvas_domain == req.institution_domain)
    )
    institution = inst_result.scalar_one_or_none()
    if not institution:
        # Derive name from domain
        name = req.institution_domain.split(".")[0].upper()
        institution = Institution(canvas_domain=req.institution_domain, name=name)
        db.add(institution)
        await db.flush()

    # Upsert user-institution link
    link_result = await db.execute(
        select(UserInstitutionLink).where(
            UserInstitutionLink.user_id == user.id,
            UserInstitutionLink.institution_id == institution.id,
        )
    )
    link = link_result.scalar_one_or_none()
    if not link:
        link = UserInstitutionLink(
            user_id=user.id, institution_id=institution.id,
            canvas_user_id=req.canvas_user_id, last_synced_at=now,
        )
        db.add(link)
    else:
        link.canvas_user_id = req.canvas_user_id
        link.last_synced_at = now

    # Get user's groups for visibility prompts
    groups_result = await db.execute(
        select(GroupMember.group_id).where(GroupMember.user_id == user.id)
    )
    user_group_ids = [row[0] for row in groups_result.all()]

    synced_courses = 0
    synced_assignments = 0
    new_courses_needing_visibility = []

    for course_data in req.courses:
        # Upsert course
        course_result = await db.execute(
            select(Course).where(
                Course.user_id == user.id,
                Course.canvas_course_id == course_data.canvas_course_id,
            )
        )
        course = course_result.scalar_one_or_none()
        is_new_course = course is None

        if not course:
            course = Course(
                user_id=user.id, institution_id=institution.id,
                canvas_course_id=course_data.canvas_course_id,
                name=course_data.name, course_code=course_data.course_code,
            )
            db.add(course)
            await db.flush()
        else:
            course.name = course_data.name
            course.course_code = course_data.course_code
            course.updated_at = now

        synced_courses += 1

        # Create visibility entries for any groups missing them
        if user_group_ids:
            groups_needing_decision = []
            for gid in user_group_ids:
                # Check if visibility entry already exists
                existing_cv = await db.execute(
                    select(CourseVisibility).where(
                        CourseVisibility.course_id == course.id,
                        CourseVisibility.group_id == gid,
                    )
                )
                if existing_cv.scalar_one_or_none():
                    continue

                cv = CourseVisibility(course_id=course.id, group_id=gid, visible=False)
                db.add(cv)
                prompt = PendingVisibilityPrompt(user_id=user.id, course_id=course.id, group_id=gid)
                db.add(prompt)

                from ..models.group import Group
                g_result = await db.execute(select(Group).where(Group.id == gid))
                g = g_result.scalar_one()
                groups_needing_decision.append({"group_id": str(gid), "group_name": g.name})

            if groups_needing_decision:
                new_courses_needing_visibility.append({
                    "course_id": str(course.id),
                    "course_name": course.name,
                    "groups": groups_needing_decision,
                })

        # Upsert assignments
        for assignment_data in course_data.assignments:
            a_result = await db.execute(
                select(Assignment).where(
                    Assignment.course_id == course.id,
                    Assignment.canvas_assignment_id == assignment_data.canvas_assignment_id,
                )
            )
            assignment = a_result.scalar_one_or_none()
            if not assignment:
                assignment = Assignment(
                    course_id=course.id,
                    canvas_assignment_id=assignment_data.canvas_assignment_id,
                    name=assignment_data.name,
                    due_at=assignment_data.due_at,
                    points_possible=assignment_data.points_possible,
                )
                db.add(assignment)
                await db.flush()
            else:
                assignment.name = assignment_data.name
                assignment.due_at = assignment_data.due_at
                assignment.points_possible = assignment_data.points_possible
                assignment.updated_at = now

            # Upsert submission
            if assignment_data.submission:
                sub_result = await db.execute(
                    select(Submission).where(Submission.assignment_id == assignment.id)
                )
                submission = sub_result.scalar_one_or_none()
                status = SubmissionStatus(assignment_data.submission.status)
                if not submission:
                    submission = Submission(
                        assignment_id=assignment.id,
                        status=status,
                        submitted_at=assignment_data.submission.submitted_at,
                        synced_at=now,
                    )
                    db.add(submission)
                else:
                    submission.status = status
                    submission.submitted_at = assignment_data.submission.submitted_at
                    submission.synced_at = now

            synced_assignments += 1

    await db.commit()

    # Return hidden course IDs so extension can skip them next sync
    hidden_result = await db.execute(
        select(Course.canvas_course_id).where(
            Course.user_id == user.id,
            Course.hidden == True,
        )
    )
    hidden_course_ids = [row[0] for row in hidden_result.all()]

    return SyncResponse(
        synced_courses=synced_courses,
        synced_assignments=synced_assignments,
        new_courses_needing_visibility=new_courses_needing_visibility,
        hidden_course_ids=hidden_course_ids,
    )


@router.delete("/account/{canvas_user_id}")
async def remove_account_data(
    canvas_user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove all synced data for a specific Canvas account."""
    # Find the institution link for this canvas user ID
    link_result = await db.execute(
        select(UserInstitutionLink).where(
            UserInstitutionLink.user_id == user.id,
            UserInstitutionLink.canvas_user_id == canvas_user_id,
        )
    )
    link = link_result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Account not found")

    # Find all courses for this user at this institution
    courses_result = await db.execute(
        select(Course).where(
            Course.user_id == user.id,
            Course.institution_id == link.institution_id,
        )
    )
    courses = courses_result.scalars().all()
    course_ids = [c.id for c in courses]

    if course_ids:
        # Delete submissions for these courses' assignments
        assignment_ids_result = await db.execute(
            select(Assignment.id).where(Assignment.course_id.in_(course_ids))
        )
        assignment_ids = [row[0] for row in assignment_ids_result.all()]

        if assignment_ids:
            await db.execute(
                delete(Submission).where(Submission.assignment_id.in_(assignment_ids))
            )
            await db.execute(
                delete(Assignment).where(Assignment.id.in_(assignment_ids))
            )

        # Delete course visibility and pending prompts
        await db.execute(
            delete(CourseVisibility).where(CourseVisibility.course_id.in_(course_ids))
        )
        await db.execute(
            delete(PendingVisibilityPrompt).where(PendingVisibilityPrompt.course_id.in_(course_ids))
        )

        # Delete courses
        await db.execute(
            delete(Course).where(Course.id.in_(course_ids))
        )

    # Delete the institution link
    await db.delete(link)
    await db.commit()

    return {"removed_courses": len(course_ids)}
