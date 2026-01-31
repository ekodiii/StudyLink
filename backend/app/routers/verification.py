import uuid
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.group import Group
from ..models.group_member import GroupMember
from ..models.assignment import Assignment
from ..models.verification_request import VerificationRequest, VerificationStatus
from ..schemas.verification import (
    VerificationCreateRequest,
    VerificationConfirmRequest,
    VerificationResponse,
)

router = APIRouter(prefix="/verification", tags=["verification"])

WORD_LIST = [
    "maple", "river", "coral", "frost", "blaze", "cedar", "pearl", "storm",
    "amber", "lunar", "plume", "delta", "haven", "crest", "bloom", "drift",
    "flint", "grove", "quill", "spark", "briar", "stone", "atlas", "fable",
    "ember", "slate", "woven", "crane", "vapor", "thorn",
]


def _gen_word() -> str:
    return random.choice(WORD_LIST)


async def _build_response(db: AsyncSession, vr: VerificationRequest) -> VerificationResponse:
    requester = (await db.execute(select(User).where(User.id == vr.requester_id))).scalar_one()
    verifier = (await db.execute(select(User).where(User.id == vr.verifier_id))).scalar_one()
    assignment = (await db.execute(select(Assignment).where(Assignment.id == vr.assignment_id))).scalar_one()
    group = (await db.execute(select(Group).where(Group.id == vr.group_id))).scalar_one()
    return VerificationResponse(
        id=str(vr.id),
        assignment_id=str(vr.assignment_id),
        assignment_name=assignment.name,
        group_id=str(vr.group_id),
        group_name=group.name,
        requester_id=str(vr.requester_id),
        requester_username=requester.username,
        verifier_id=str(vr.verifier_id),
        verifier_username=verifier.username,
        status=vr.status.value if isinstance(vr.status, VerificationStatus) else vr.status,
        verification_word=vr.verification_word,
        requested_at=vr.requested_at,
        verified_at=vr.verified_at,
    )


@router.post("/request", response_model=VerificationResponse)
async def create_verification(
    req: VerificationCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group_id = uuid.UUID(req.group_id)
    verifier_id = uuid.UUID(req.verifier_id)
    assignment_id = uuid.UUID(req.assignment_id)

    # Verify both are members
    for uid in [user.id, verifier_id]:
        result = await db.execute(
            select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == uid)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="User is not a member of this group")

    if verifier_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot verify your own assignment")

    # Check no active request exists
    existing = await db.execute(
        select(VerificationRequest).where(
            VerificationRequest.assignment_id == assignment_id,
            VerificationRequest.requester_id == user.id,
            VerificationRequest.group_id == group_id,
            VerificationRequest.status.in_([VerificationStatus.pending, VerificationStatus.verified]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Active verification request already exists")

    vr = VerificationRequest(
        assignment_id=assignment_id,
        group_id=group_id,
        requester_id=user.id,
        verifier_id=verifier_id,
        verification_word=_gen_word(),
    )
    db.add(vr)
    await db.commit()
    await db.refresh(vr)
    return await _build_response(db, vr)


@router.get("/pending", response_model=list[VerificationResponse])
async def get_pending(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VerificationRequest).where(
            VerificationRequest.verifier_id == user.id,
            VerificationRequest.status == VerificationStatus.pending,
        )
    )
    return [await _build_response(db, vr) for vr in result.scalars().all()]


@router.get("/sent", response_model=list[VerificationResponse])
async def get_sent(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VerificationRequest).where(
            VerificationRequest.requester_id == user.id,
            VerificationRequest.status.in_([VerificationStatus.pending, VerificationStatus.verified]),
        )
    )
    return [await _build_response(db, vr) for vr in result.scalars().all()]


@router.post("/{request_id}/verify", response_model=VerificationResponse)
async def verify_request(
    request_id: uuid.UUID,
    req: VerificationConfirmRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VerificationRequest).where(VerificationRequest.id == request_id))
    vr = result.scalar_one_or_none()
    if not vr:
        raise HTTPException(status_code=404, detail="Verification request not found")
    if vr.verifier_id != user.id:
        raise HTTPException(status_code=403, detail="Only the assigned verifier can confirm")
    if vr.status != VerificationStatus.pending:
        raise HTTPException(status_code=400, detail="Request is not pending")
    if req.verification_word.strip().lower() != vr.verification_word.lower():
        raise HTTPException(status_code=400, detail="Incorrect verification word")

    vr.status = VerificationStatus.verified
    vr.verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(vr)
    return await _build_response(db, vr)


@router.post("/{request_id}/cancel", response_model=VerificationResponse)
async def cancel_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VerificationRequest).where(VerificationRequest.id == request_id))
    vr = result.scalar_one_or_none()
    if not vr:
        raise HTTPException(status_code=404, detail="Verification request not found")
    if vr.requester_id != user.id:
        raise HTTPException(status_code=403, detail="Only the requester can cancel")
    if vr.status not in (VerificationStatus.pending, VerificationStatus.verified):
        raise HTTPException(status_code=400, detail="Cannot cancel this request")

    vr.status = VerificationStatus.cancelled
    await db.commit()
    await db.refresh(vr)
    return await _build_response(db, vr)


@router.post("/{request_id}/revoke", response_model=VerificationResponse)
async def revoke_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VerificationRequest).where(VerificationRequest.id == request_id))
    vr = result.scalar_one_or_none()
    if not vr:
        raise HTTPException(status_code=404, detail="Verification request not found")
    if vr.verifier_id != user.id:
        raise HTTPException(status_code=403, detail="Only the verifier can revoke")
    if vr.status != VerificationStatus.verified:
        raise HTTPException(status_code=400, detail="Can only revoke verified requests")

    vr.status = VerificationStatus.revoked
    await db.commit()
    await db.refresh(vr)
    return await _build_response(db, vr)
