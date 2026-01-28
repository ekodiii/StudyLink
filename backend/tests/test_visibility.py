import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course_visibility import CourseVisibility
from app.models.pending_visibility_prompt import PendingVisibilityPrompt


SYNC_PAYLOAD = {
    "institution_domain": "umd.instructure.com",
    "canvas_user_id": "12345",
    "courses": [
        {
            "canvas_course_id": "98765",
            "name": "CMSC132",
            "course_code": "CMSC132",
            "assignments": [
                {
                    "canvas_assignment_id": "11111",
                    "name": "Project 1",
                    "due_at": "2025-02-01T23:59:00Z",
                    "points_possible": 100,
                    "submission": {"status": "submitted", "submitted_at": "2025-01-28T15:30:00Z"},
                }
            ],
        },
        {
            "canvas_course_id": "55555",
            "name": "PHYS260",
            "course_code": "PHYS260",
            "assignments": [],
        },
    ],
}


async def _setup_group_and_sync(client, auth_headers):
    """Helper: create group, then sync courses."""
    group_resp = await client.post("/groups", json={"name": "Study Group"}, headers=auth_headers)
    group = group_resp.json()
    sync_resp = await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)
    return group, sync_resp.json()


@pytest.mark.asyncio
async def test_pending_visibility(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    await _setup_group_and_sync(client, auth_headers)

    resp = await client.get("/visibility/pending", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["pending"]) == 2  # Two new courses
    course_names = {c["course_name"] for c in data["pending"]}
    assert course_names == {"CMSC132", "PHYS260"}
    # Each course should list the group
    for course in data["pending"]:
        assert len(course["groups"]) == 1
        assert course["groups"][0]["group_name"] == "Study Group"


@pytest.mark.asyncio
async def test_decide_visibility(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    group, sync_data = await _setup_group_and_sync(client, auth_headers)

    # Get pending to find course IDs
    pending = await client.get("/visibility/pending", headers=auth_headers)
    courses = pending.json()["pending"]

    decisions = [
        {"course_id": courses[0]["course_id"], "group_id": courses[0]["groups"][0]["group_id"], "visible": True},
        {"course_id": courses[1]["course_id"], "group_id": courses[1]["groups"][0]["group_id"], "visible": False},
    ]

    resp = await client.post("/visibility/decide", json={"decisions": decisions}, headers=auth_headers)
    assert resp.status_code == 200

    # Pending should be empty now
    pending_after = await client.get("/visibility/pending", headers=auth_headers)
    assert len(pending_after.json()["pending"]) == 0

    # Settings should reflect decisions
    settings = await client.get("/visibility/settings", headers=auth_headers)
    assert settings.status_code == 200
    items = settings.json()["settings"]
    assert len(items) == 2
    visible_items = {i["course_name"]: i["visible"] for i in items}
    assert visible_items["CMSC132"] is True
    assert visible_items["PHYS260"] is False


@pytest.mark.asyncio
async def test_update_visibility_settings(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    group, _ = await _setup_group_and_sync(client, auth_headers)

    # Decide first
    pending = await client.get("/visibility/pending", headers=auth_headers)
    courses = pending.json()["pending"]
    decisions = [
        {"course_id": c["course_id"], "group_id": c["groups"][0]["group_id"], "visible": False}
        for c in courses
    ]
    await client.post("/visibility/decide", json={"decisions": decisions}, headers=auth_headers)

    # Now flip one to visible via PATCH settings
    flip = [{"course_id": courses[0]["course_id"], "group_id": courses[0]["groups"][0]["group_id"], "visible": True}]
    resp = await client.patch("/visibility/settings", json={"decisions": flip}, headers=auth_headers)
    assert resp.status_code == 200

    settings = await client.get("/visibility/settings", headers=auth_headers)
    items = {i["course_name"]: i["visible"] for i in settings.json()["settings"]}
    assert items[courses[0]["course_name"]] is True


@pytest.mark.asyncio
async def test_no_pending_without_groups(client: AsyncClient, auth_headers: dict):
    # Sync without any groups
    await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)
    resp = await client.get("/visibility/pending", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["pending"]) == 0
