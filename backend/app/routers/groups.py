import random
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.group import Group
from ..models.group_member import GroupMember
from ..models.user_institution_link import UserInstitutionLink
from ..models.course import Course
from ..models.course_visibility import CourseVisibility
from ..models.pending_visibility_prompt import PendingVisibilityPrompt
from ..schemas.group import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupResponse,
    GroupDetailResponse,
    MemberBrief,
    MemberInfo,
    JoinGroupRequest,
    TransferLeadershipRequest,
)

router = APIRouter(prefix="/groups", tags=["groups"])


def _gen_invite_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=8))


async def _verify_member(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this group")


async def _verify_leader(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.leader_id != user_id:
        raise HTTPException(status_code=403, detail="Only the group leader can do this")
    return group


async def _create_visibility_for_user_group(db: AsyncSession, user_id: uuid.UUID, group_id: uuid.UUID):
    """Create visibility entries + pending prompts for all user's non-hidden courses in a group."""
    courses_result = await db.execute(
        select(Course).where(Course.user_id == user_id, Course.hidden == False)
    )
    for course in courses_result.scalars().all():
        existing = await db.execute(
            select(CourseVisibility).where(
                CourseVisibility.course_id == course.id,
                CourseVisibility.group_id == group_id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(CourseVisibility(course_id=course.id, group_id=group_id, visible=False))
        db.add(PendingVisibilityPrompt(user_id=user_id, course_id=course.id, group_id=group_id))


@router.post("", response_model=GroupResponse)
async def create_group(
    req: GroupCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    invite_code = _gen_invite_code()
    group = Group(name=req.name, invite_code=invite_code, leader_id=user.id)
    db.add(group)
    await db.flush()

    member = GroupMember(group_id=group.id, user_id=user.id)
    db.add(member)

    # Auto-create visibility entries for all user's courses
    await _create_visibility_for_user_group(db, user.id, group.id)

    await db.commit()
    await db.refresh(group)

    return GroupResponse(
        id=str(group.id), name=group.name, invite_code=group.invite_code,
        is_leader=True, member_count=1, created_at=group.created_at,
    )


@router.get("", response_model=list[GroupResponse])
async def list_groups(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Group, func.count(GroupMember.id).label("cnt"))
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(Group.id.in_(
            select(GroupMember.group_id).where(GroupMember.user_id == user.id)
        ))
        .group_by(Group.id)
    )
    rows = result.all()
    return [
        GroupResponse(
            id=str(g.id), name=g.name, invite_code=g.invite_code,
            is_leader=(g.leader_id == user.id), member_count=cnt, created_at=g.created_at,
        )
        for g, cnt in rows
    ]


@router.get("/{group_id}", response_model=GroupDetailResponse)
async def get_group(group_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_member(db, group_id, user.id)

    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Get leader
    leader_result = await db.execute(select(User).where(User.id == group.leader_id))
    leader = leader_result.scalar_one()

    # Get members with last_synced_at
    members_result = await db.execute(
        select(User, GroupMember.joined_at)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at)
    )
    members = []
    for u, joined_at in members_result.all():
        # Get last sync time
        link_result = await db.execute(
            select(func.max(UserInstitutionLink.last_synced_at)).where(UserInstitutionLink.user_id == u.id)
        )
        last_synced = link_result.scalar()
        members.append(MemberInfo(
            id=str(u.id), username=u.username, discriminator=u.discriminator,
            joined_at=joined_at, last_synced_at=last_synced,
        ))

    return GroupDetailResponse(
        id=str(group.id), name=group.name, invite_code=group.invite_code,
        assignment_view_enabled=group.assignment_view_enabled,
        leader=MemberBrief(id=str(leader.id), username=leader.username, discriminator=leader.discriminator),
        members=members,
    )


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID, req: GroupUpdateRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    group = await _verify_leader(db, group_id, user.id)
    if req.name is not None:
        group.name = req.name
    if req.assignment_view_enabled is not None:
        group.assignment_view_enabled = req.assignment_view_enabled
    await db.commit()
    await db.refresh(group)

    cnt_result = await db.execute(select(func.count()).where(GroupMember.group_id == group_id))
    cnt = cnt_result.scalar()

    return GroupResponse(
        id=str(group.id), name=group.name, invite_code=group.invite_code,
        is_leader=True, member_count=cnt, created_at=group.created_at,
    )


@router.delete("/{group_id}")
async def delete_group(group_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_leader(db, group_id, user.id)
    await db.execute(delete(Group).where(Group.id == group_id))
    await db.commit()
    return {"ok": True}


@router.delete("/{group_id}/leave")
async def leave_group(group_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_member(db, group_id, user.id)

    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one()

    # Remove member
    await db.execute(
        delete(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id)
    )

    # Check remaining members
    remaining = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id).order_by(GroupMember.joined_at).limit(1)
    )
    oldest = remaining.scalar_one_or_none()

    if not oldest:
        # Last member left, delete group
        await db.execute(delete(Group).where(Group.id == group_id))
    elif group.leader_id == user.id:
        # Transfer leadership to oldest member
        group.leader_id = oldest.user_id
    await db.commit()
    return {"ok": True}


@router.post("/{group_id}/regenerate-invite")
async def regenerate_invite(group_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    group = await _verify_leader(db, group_id, user.id)
    group.invite_code = _gen_invite_code()
    await db.commit()
    return {"invite_code": group.invite_code}


@router.post("/join", response_model=GroupResponse)
async def join_group(req: JoinGroupRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Group).where(Group.invite_code == req.invite_code.upper()))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    # Check if already a member
    existing = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already a member")

    member = GroupMember(group_id=group.id, user_id=user.id)
    db.add(member)

    # Auto-create visibility entries for all user's courses
    await _create_visibility_for_user_group(db, user.id, group.id)

    await db.commit()

    cnt_result = await db.execute(select(func.count()).where(GroupMember.group_id == group.id))
    cnt = cnt_result.scalar()

    return GroupResponse(
        id=str(group.id), name=group.name, invite_code=group.invite_code,
        is_leader=(group.leader_id == user.id), member_count=cnt, created_at=group.created_at,
    )


@router.delete("/{group_id}/members/{user_id}")
async def remove_member(
    group_id: uuid.UUID, user_id: uuid.UUID,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    if user_id == user.id:
        # Self-removal = leave
        return await leave_group(group_id, user, db)
    await _verify_leader(db, group_id, user.id)
    await db.execute(
        delete(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )
    await db.commit()
    return {"ok": True}


@router.post("/{group_id}/transfer-leadership")
async def transfer_leadership(
    group_id: uuid.UUID, req: TransferLeadershipRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    group = await _verify_leader(db, group_id, user.id)
    new_leader_id = uuid.UUID(req.new_leader_id)

    # Verify new leader is a member
    result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == new_leader_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is not a member of this group")

    group.leader_id = new_leader_id
    await db.commit()
    return {"ok": True}
