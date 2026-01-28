import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.institution import Institution
from app.models.course import Course
from app.models.assignment import Assignment
from app.models.submission import Submission, SubmissionStatus
from app.models.user_institution_link import UserInstitutionLink
from app.models.group import Group
from app.models.group_member import GroupMember
from app.models.course_visibility import CourseVisibility
from app.models.pending_visibility_prompt import PendingVisibilityPrompt


SYNC_PAYLOAD = {
    "institution_domain": "umd.instructure.com",
    "canvas_user_id": "12345",
    "courses": [
        {
            "canvas_course_id": "98765",
            "name": "Intro to Programming",
            "course_code": "CMSC132",
            "assignments": [
                {
                    "canvas_assignment_id": "11111",
                    "name": "Project 1",
                    "due_at": "2025-02-01T23:59:00Z",
                    "points_possible": 100,
                    "submission": {
                        "status": "submitted",
                        "submitted_at": "2025-01-28T15:30:00Z",
                    },
                },
                {
                    "canvas_assignment_id": "22222",
                    "name": "Project 2",
                    "due_at": "2025-02-15T23:59:00Z",
                    "points_possible": 50,
                    "submission": {"status": "unsubmitted"},
                },
            ],
        }
    ],
}


@pytest.mark.asyncio
async def test_sync_creates_institution(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    resp = await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced_courses"] == 1
    assert data["synced_assignments"] == 2

    # Verify institution created
    result = await db_session.execute(select(Institution))
    inst = result.scalar_one()
    assert inst.canvas_domain == "umd.instructure.com"
    assert inst.name == "UMD"


@pytest.mark.asyncio
async def test_sync_creates_courses_and_assignments(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)

    courses = (await db_session.execute(select(Course))).scalars().all()
    assert len(courses) == 1
    assert courses[0].name == "Intro to Programming"
    assert courses[0].course_code == "CMSC132"

    assignments = (await db_session.execute(select(Assignment))).scalars().all()
    assert len(assignments) == 2
    names = {a.name for a in assignments}
    assert names == {"Project 1", "Project 2"}


@pytest.mark.asyncio
async def test_sync_creates_submissions(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)

    subs = (await db_session.execute(select(Submission))).scalars().all()
    assert len(subs) == 2
    statuses = {s.status for s in subs}
    assert SubmissionStatus.submitted in statuses
    assert SubmissionStatus.unsubmitted in statuses

    submitted = [s for s in subs if s.status == SubmissionStatus.submitted][0]
    assert submitted.submitted_at is not None


@pytest.mark.asyncio
async def test_sync_creates_user_institution_link(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)

    links = (await db_session.execute(select(UserInstitutionLink))).scalars().all()
    assert len(links) == 1
    assert links[0].canvas_user_id == "12345"
    assert links[0].last_synced_at is not None


@pytest.mark.asyncio
async def test_sync_upserts_on_second_call(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)
    # Second sync with updated data
    updated = {**SYNC_PAYLOAD}
    updated["courses"] = [
        {
            **SYNC_PAYLOAD["courses"][0],
            "name": "Intro to Programming (Updated)",
            "assignments": [
                {
                    "canvas_assignment_id": "11111",
                    "name": "Project 1 v2",
                    "due_at": "2025-02-05T23:59:00Z",
                    "points_possible": 150,
                    "submission": {"status": "graded", "submitted_at": "2025-01-28T15:30:00Z"},
                },
            ],
        }
    ]
    resp = await client.post("/sync", json=updated, headers=auth_headers)
    assert resp.status_code == 200

    # Should still be 1 course, not 2
    courses = (await db_session.execute(select(Course))).scalars().all()
    assert len(courses) == 1
    assert courses[0].name == "Intro to Programming (Updated)"

    # Assignment name should be updated
    a = (await db_session.execute(select(Assignment).where(Assignment.canvas_assignment_id == "11111"))).scalar_one()
    assert a.name == "Project 1 v2"
    assert a.points_possible == 150

    # Submission should be updated to graded
    sub = (await db_session.execute(select(Submission).where(Submission.assignment_id == a.id))).scalar_one()
    assert sub.status == SubmissionStatus.graded


@pytest.mark.asyncio
async def test_sync_creates_visibility_prompts_when_in_group(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    # Create group first
    group_resp = await client.post("/groups", json={"name": "Study Group"}, headers=auth_headers)
    group_id = group_resp.json()["id"]

    # Sync — should create visibility entries
    resp = await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["new_courses_needing_visibility"]) == 1
    assert data["new_courses_needing_visibility"][0]["course_name"] == "Intro to Programming"

    # Verify DB entries
    cv_rows = (await db_session.execute(select(CourseVisibility))).scalars().all()
    assert len(cv_rows) == 1
    assert cv_rows[0].visible is False

    prompts = (await db_session.execute(select(PendingVisibilityPrompt))).scalars().all()
    assert len(prompts) == 1


@pytest.mark.asyncio
async def test_sync_no_visibility_prompts_without_group(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    resp = await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["new_courses_needing_visibility"] == []

    prompts = (await db_session.execute(select(PendingVisibilityPrompt))).scalars().all()
    assert len(prompts) == 0


@pytest.mark.asyncio
async def test_sync_unauthorized(client: AsyncClient):
    resp = await client.post("/sync", json=SYNC_PAYLOAD)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sync_all_submission_statuses(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    payload = {
        "institution_domain": "test.instructure.com",
        "canvas_user_id": "999",
        "courses": [
            {
                "canvas_course_id": "100",
                "name": "Test Course",
                "assignments": [
                    {"canvas_assignment_id": "1", "name": "A1", "submission": {"status": "submitted", "submitted_at": "2025-01-01T00:00:00Z"}},
                    {"canvas_assignment_id": "2", "name": "A2", "submission": {"status": "late", "submitted_at": "2025-01-02T00:00:00Z"}},
                    {"canvas_assignment_id": "3", "name": "A3", "submission": {"status": "missing"}},
                    {"canvas_assignment_id": "4", "name": "A4", "submission": {"status": "graded", "submitted_at": "2025-01-03T00:00:00Z"}},
                    {"canvas_assignment_id": "5", "name": "A5", "submission": {"status": "unsubmitted"}},
                ],
            }
        ],
    }
    resp = await client.post("/sync", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["synced_assignments"] == 5

    subs = (await db_session.execute(select(Submission))).scalars().all()
    statuses = {s.status for s in subs}
    assert statuses == {
        SubmissionStatus.submitted,
        SubmissionStatus.late,
        SubmissionStatus.missing,
        SubmissionStatus.graded,
        SubmissionStatus.unsubmitted,
    }
