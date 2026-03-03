import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Assignment,
    Course,
    Group,
    GroupMember,
    Institution,
    PendingVisibilityPrompt,
    UserInstitutionLink,
    VerificationRequest,
    VerificationStatus,
)
from .database import async_session

logger = logging.getLogger(__name__)

COURSE_STALE_DAYS = 14       # 2 weeks
ASSIGNMENT_OLD_DAYS = 180    # 6 months
PROMPT_STALE_DAYS = 14       # 2 weeks
VERIFICATION_OLD_DAYS = 180  # 6 months


async def run_cleanup() -> dict[str, int]:
    """Run all cleanup tasks. Each task commits independently so one failure doesn't block the rest."""
    logger.info("Starting scheduled cleanup...")
    results = {}

    async with async_session() as session:
        results["stale_courses"] = await _delete_stale_courses(session)
        results["old_assignments"] = await _delete_old_assignments(session)
        results["empty_groups"] = await _delete_empty_groups(session)
        results["stale_prompts"] = await _delete_stale_prompts(session)
        results["old_verifications"] = await _delete_old_verifications(session)
        results["orphaned_institutions"] = await _delete_orphaned_institutions(session)

    total = sum(results.values())
    if total > 0:
        logger.info(f"Cleanup complete: {results}")
    else:
        logger.info("Cleanup complete: nothing to delete")
    return results


async def _delete_stale_courses(session: AsyncSession) -> int:
    """Delete courses not synced in over 2 weeks.
    DB cascades: assignments, submissions, verification_requests, course_visibility, pending_prompts.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=COURSE_STALE_DAYS)
    result = await session.execute(
        delete(Course).where(Course.updated_at < cutoff)
    )
    await session.commit()
    return result.rowcount


async def _delete_old_assignments(session: AsyncSession) -> int:
    """Delete assignments with due_at older than 6 months (from courses that are still active).
    DB cascades: submissions, verification_requests.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=ASSIGNMENT_OLD_DAYS)
    result = await session.execute(
        delete(Assignment).where(
            Assignment.due_at.isnot(None),
            Assignment.due_at < cutoff,
        )
    )
    await session.commit()
    return result.rowcount


async def _delete_empty_groups(session: AsyncSession) -> int:
    """Delete groups with no members.
    DB cascades: course_visibility, pending_prompts, verification_requests.
    """
    result = await session.execute(
        delete(Group).where(
            ~exists(
                select(GroupMember.id).where(GroupMember.group_id == Group.id)
            )
        )
    )
    await session.commit()
    return result.rowcount


async def _delete_stale_prompts(session: AsyncSession) -> int:
    """Delete pending visibility prompts older than 2 weeks."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=PROMPT_STALE_DAYS)
    result = await session.execute(
        delete(PendingVisibilityPrompt).where(
            PendingVisibilityPrompt.created_at < cutoff
        )
    )
    await session.commit()
    return result.rowcount


async def _delete_old_verifications(session: AsyncSession) -> int:
    """Delete resolved verification requests older than 6 months."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=VERIFICATION_OLD_DAYS)
    result = await session.execute(
        delete(VerificationRequest).where(
            VerificationRequest.status.in_([
                VerificationStatus.verified,
                VerificationStatus.cancelled,
                VerificationStatus.revoked,
            ]),
            VerificationRequest.requested_at < cutoff,
        )
    )
    await session.commit()
    return result.rowcount


async def _delete_orphaned_institutions(session: AsyncSession) -> int:
    """Delete institutions with no linked users."""
    result = await session.execute(
        delete(Institution).where(
            ~exists(
                select(UserInstitutionLink.id).where(
                    UserInstitutionLink.institution_id == Institution.id
                )
            )
        )
    )
    await session.commit()
    return result.rowcount


async def cleanup_loop():
    """Background loop: run cleanup 60s after boot, then every 24 hours."""
    await asyncio.sleep(60)
    while True:
        try:
            await run_cleanup()
        except Exception:
            logger.exception("Cleanup task failed")
        await asyncio.sleep(86400)
