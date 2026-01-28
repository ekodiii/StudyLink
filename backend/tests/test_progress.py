import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


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
                    "submission": {"status": "submitted", "submitted_at": "2025-01-28T15:30:00Z"},
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
async def test_progress_shows_visible_courses(client: AsyncClient, auth_headers: dict, auth_headers2: dict):
    # User1 creates group, syncs data
    group_resp = await client.post("/groups", json={"name": "Progress Group"}, headers=auth_headers)
    group = group_resp.json()

    # User2 joins
    await client.post("/groups/join", json={"invite_code": group["invite_code"]}, headers=auth_headers2)

    # User1 syncs
    await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)

    # Make course visible
    pending = await client.get("/visibility/pending", headers=auth_headers)
    course = pending.json()["pending"][0]
    await client.post(
        "/visibility/decide",
        json={"decisions": [{"course_id": course["course_id"], "group_id": course["groups"][0]["group_id"], "visible": True}]},
        headers=auth_headers,
    )

    # Get progress
    resp = await client.get(f"/groups/{group['id']}/progress", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_name"] == "Progress Group"
    assert len(data["members"]) == 2

    # Find user1 in members
    user1_member = [m for m in data["members"] if m["username"] == "testuser"][0]
    assert len(user1_member["courses"]) == 1
    assert user1_member["courses"][0]["course_code"] == "CMSC132"
    assert len(user1_member["courses"][0]["assignments"]) == 2

    # Check assignment statuses
    assignments = {a["name"]: a for a in user1_member["courses"][0]["assignments"]}
    assert assignments["Project 1"]["status"] == "submitted"
    assert assignments["Project 2"]["status"] == "unsubmitted"

    # User2 has no courses (didn't sync)
    user2_member = [m for m in data["members"] if m["username"] == "otheruser"][0]
    assert len(user2_member["courses"]) == 0


@pytest.mark.asyncio
async def test_progress_hides_invisible_courses(client: AsyncClient, auth_headers: dict, auth_headers2: dict):
    group_resp = await client.post("/groups", json={"name": "Hidden Group"}, headers=auth_headers)
    group = group_resp.json()
    await client.post("/groups/join", json={"invite_code": group["invite_code"]}, headers=auth_headers2)

    await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)

    # Decide NOT to share
    pending = await client.get("/visibility/pending", headers=auth_headers)
    course = pending.json()["pending"][0]
    await client.post(
        "/visibility/decide",
        json={"decisions": [{"course_id": course["course_id"], "group_id": course["groups"][0]["group_id"], "visible": False}]},
        headers=auth_headers,
    )

    # Progress should show no courses for user1
    resp = await client.get(f"/groups/{group['id']}/progress", headers=auth_headers)
    user1 = [m for m in resp.json()["members"] if m["username"] == "testuser"][0]
    assert len(user1["courses"]) == 0


@pytest.mark.asyncio
async def test_progress_nonmember_forbidden(client: AsyncClient, auth_headers: dict, auth_headers2: dict):
    group_resp = await client.post("/groups", json={"name": "Private Group"}, headers=auth_headers)
    group = group_resp.json()

    resp = await client.get(f"/groups/{group['id']}/progress", headers=auth_headers2)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_progress_date_filter(client: AsyncClient, auth_headers: dict):
    group_resp = await client.post("/groups", json={"name": "Filter Group"}, headers=auth_headers)
    group = group_resp.json()

    await client.post("/sync", json=SYNC_PAYLOAD, headers=auth_headers)

    # Make visible
    pending = await client.get("/visibility/pending", headers=auth_headers)
    course = pending.json()["pending"][0]
    await client.post(
        "/visibility/decide",
        json={"decisions": [{"course_id": course["course_id"], "group_id": course["groups"][0]["group_id"], "visible": True}]},
        headers=auth_headers,
    )

    # Filter: only assignments due before Feb 10
    resp = await client.get(f"/groups/{group['id']}/progress?due_before=2025-02-10", headers=auth_headers)
    user1 = [m for m in resp.json()["members"] if m["username"] == "testuser"][0]
    assert len(user1["courses"][0]["assignments"]) == 1
    assert user1["courses"][0]["assignments"][0]["name"] == "Project 1"
