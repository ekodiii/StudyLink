import uuid as uuid_mod
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.course import Course
from ..models.group import Group
from ..models.institution import Institution
from ..models.course_visibility import CourseVisibility
from ..models.pending_visibility_prompt import PendingVisibilityPrompt
from ..schemas.visibility import (
    VisibilityDecideRequest,
    PendingResponse,
    PendingCourse,
    PendingCourseGroup,
    VisibilitySettingsResponse,
    VisibilitySettingItem,
)

router = APIRouter(prefix="/visibility", tags=["visibility"])


@router.get("/pending", response_model=PendingResponse)
async def get_pending(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PendingVisibilityPrompt, Course, Group)
        .join(Course, PendingVisibilityPrompt.course_id == Course.id)
        .join(Group, PendingVisibilityPrompt.group_id == Group.id)
        .where(PendingVisibilityPrompt.user_id == user.id, Course.hidden == False)
    )
    rows = result.all()

    # Group by course
    courses_map: dict[str, PendingCourse] = {}
    for prompt, course, group in rows:
        cid = str(course.id)
        if cid not in courses_map:
            # Get institution name
            inst_result = await db.execute(select(Institution).where(Institution.id == course.institution_id))
            inst = inst_result.scalar_one_or_none()
            courses_map[cid] = PendingCourse(
                course_id=cid, course_name=course.name,
                course_code=course.course_code,
                institution=inst.name if inst else None,
            )
        courses_map[cid].groups.append(PendingCourseGroup(group_id=str(group.id), group_name=group.name))

    return PendingResponse(pending=list(courses_map.values()))


@router.post("/decide")
async def decide_visibility(
    req: VisibilityDecideRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    for decision in req.decisions:
        course_uid = uuid_mod.UUID(decision.course_id)
        group_uid = uuid_mod.UUID(decision.group_id)

        # Update visibility
        result = await db.execute(
            select(CourseVisibility).where(
                CourseVisibility.course_id == course_uid,
                CourseVisibility.group_id == group_uid,
            )
        )
        cv = result.scalar_one_or_none()
        if cv:
            cv.visible = decision.visible
            cv.decided_at = now

        # Remove pending prompt
        prompt_result = await db.execute(
            select(PendingVisibilityPrompt).where(
                PendingVisibilityPrompt.user_id == user.id,
                PendingVisibilityPrompt.course_id == course_uid,
                PendingVisibilityPrompt.group_id == group_uid,
            )
        )
        prompt = prompt_result.scalar_one_or_none()
        if prompt:
            await db.delete(prompt)

    await db.commit()
    return {"ok": True}


@router.get("/settings", response_model=VisibilitySettingsResponse)
async def get_settings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CourseVisibility, Course, Group)
        .join(Course, CourseVisibility.course_id == Course.id)
        .join(Group, CourseVisibility.group_id == Group.id)
        .where(Course.user_id == user.id)
    )
    rows = result.all()
    return VisibilitySettingsResponse(
        settings=[
            VisibilitySettingItem(
                course_id=str(cv.course_id), course_name=course.name,
                group_id=str(cv.group_id), group_name=group.name,
                visible=cv.visible,
            )
            for cv, course, group in rows
        ]
    )


@router.patch("/settings")
async def update_settings(
    req: VisibilityDecideRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await decide_visibility(req, user, db)
