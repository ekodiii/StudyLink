import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.course import Course
from ..schemas.user import UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(id=str(user.id), username=user.username, discriminator=user.discriminator)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    req: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Find available discriminator for new username
    disc = user.discriminator
    result = await db.execute(
        select(func.count()).where(User.username == req.username, User.discriminator == disc, User.id != user.id)
    )
    if result.scalar() > 0:
        # Collision — find new discriminator
        for _ in range(100):
            disc = f"{random.randint(0, 9999):04d}"
            check = await db.execute(
                select(func.count()).where(User.username == req.username, User.discriminator == disc)
            )
            if check.scalar() == 0:
                break
        else:
            raise HTTPException(status_code=409, detail="Username unavailable")

    user.username = req.username
    user.discriminator = disc
    await db.commit()
    await db.refresh(user)
    return UserResponse(id=str(user.id), username=user.username, discriminator=user.discriminator)


@router.get("/me/courses")
async def get_my_courses(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Course).where(Course.user_id == user.id).order_by(Course.name)
    )
    courses = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "course_code": c.course_code,
            "canvas_course_id": c.canvas_course_id,
            "hidden": c.hidden,
        }
        for c in courses
    ]


@router.patch("/me/courses/{course_id}")
async def update_my_course(
    course_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as uuid_mod
    result = await db.execute(
        select(Course).where(Course.id == uuid_mod.UUID(course_id), Course.user_id == user.id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course.hidden = not course.hidden
    await db.commit()
    return {"id": str(course.id), "hidden": course.hidden}


@router.get("/search")
async def search_users(q: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Query too short")
    result = await db.execute(select(User).where(User.username.ilike(f"%{q}%")).limit(20))
    users = result.scalars().all()
    return [{"id": str(u.id), "username": u.username, "discriminator": u.discriminator} for u in users]
