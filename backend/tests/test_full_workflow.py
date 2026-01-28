"""
End-to-end workflow test: simulates the full user journey.

1. Two users exist
2. User1 creates a group
3. User2 joins via invite code
4. User1 syncs Canvas data via extension
5. User1 gets visibility prompt, decides to share one course
6. User2 views group progress — sees User1's shared assignments
7. User1 syncs again with updated submission statuses
8. User2 checks progress — sees updated statuses
9. User1 transfers leadership to User2
10. User2 renames the group
11. User1 leaves the group
"""
import pytest
from httpx import AsyncClient


INITIAL_SYNC = {
    "institution_domain": "umd.instructure.com",
    "canvas_user_id": "12345",
    "courses": [
        {
            "canvas_course_id": "100",
            "name": "Intro to CS",
            "course_code": "CMSC132",
            "assignments": [
                {
                    "canvas_assignment_id": "1",
                    "name": "HW 1",
                    "due_at": "2025-02-01T23:59:00Z",
                    "points_possible": 100,
                    "submission": {"status": "submitted", "submitted_at": "2025-01-28T10:00:00Z"},
                },
                {
                    "canvas_assignment_id": "2",
                    "name": "HW 2",
                    "due_at": "2025-02-15T23:59:00Z",
                    "points_possible": 50,
                    "submission": {"status": "unsubmitted"},
                },
            ],
        },
        {
            "canvas_course_id": "200",
            "name": "Physics",
            "course_code": "PHYS260",
            "assignments": [
                {
                    "canvas_assignment_id": "3",
                    "name": "Lab Report",
                    "due_at": "2025-02-10T23:59:00Z",
                    "points_possible": 75,
                    "submission": {"status": "missing"},
                },
            ],
        },
    ],
}

UPDATED_SYNC = {
    "institution_domain": "umd.instructure.com",
    "canvas_user_id": "12345",
    "courses": [
        {
            "canvas_course_id": "100",
            "name": "Intro to CS",
            "course_code": "CMSC132",
            "assignments": [
                {
                    "canvas_assignment_id": "1",
                    "name": "HW 1",
                    "due_at": "2025-02-01T23:59:00Z",
                    "points_possible": 100,
                    "submission": {"status": "graded", "submitted_at": "2025-01-28T10:00:00Z"},
                },
                {
                    "canvas_assignment_id": "2",
                    "name": "HW 2",
                    "due_at": "2025-02-15T23:59:00Z",
                    "points_possible": 50,
                    "submission": {"status": "submitted", "submitted_at": "2025-02-10T08:00:00Z"},
                },
            ],
        },
        {
            "canvas_course_id": "200",
            "name": "Physics",
            "course_code": "PHYS260",
            "assignments": [
                {
                    "canvas_assignment_id": "3",
                    "name": "Lab Report",
                    "due_at": "2025-02-10T23:59:00Z",
                    "points_possible": 75,
                    "submission": {"status": "late", "submitted_at": "2025-02-11T02:00:00Z"},
                },
            ],
        },
    ],
}


@pytest.mark.asyncio
async def test_full_workflow(client: AsyncClient, auth_headers: dict, auth_headers2: dict, test_user: ..., test_user2: ...):
    # --- Step 1: Verify users ---
    me1 = await client.get("/users/me", headers=auth_headers)
    assert me1.status_code == 200
    assert me1.json()["username"] == "testuser"

    me2 = await client.get("/users/me", headers=auth_headers2)
    assert me2.status_code == 200
    assert me2.json()["username"] == "otheruser"

    # --- Step 2: User1 creates group ---
    group_resp = await client.post("/groups", json={"name": "CMSC132 Study Group"}, headers=auth_headers)
    assert group_resp.status_code == 200
    group = group_resp.json()
    group_id = group["id"]
    assert group["is_leader"] is True
    assert group["member_count"] == 1

    # --- Step 3: User2 joins ---
    join_resp = await client.post("/groups/join", json={"invite_code": group["invite_code"]}, headers=auth_headers2)
    assert join_resp.status_code == 200
    assert join_resp.json()["member_count"] == 2

    # Verify group detail
    detail = await client.get(f"/groups/{group_id}", headers=auth_headers)
    assert len(detail.json()["members"]) == 2

    # --- Step 4: User1 syncs Canvas data ---
    sync_resp = await client.post("/sync", json=INITIAL_SYNC, headers=auth_headers)
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data["synced_courses"] == 2
    assert sync_data["synced_assignments"] == 3
    assert len(sync_data["new_courses_needing_visibility"]) == 2

    # --- Step 5: User1 decides visibility ---
    pending = await client.get("/visibility/pending", headers=auth_headers)
    pending_courses = pending.json()["pending"]
    assert len(pending_courses) == 2

    # Share CMSC132, hide PHYS260
    cmsc = next(c for c in pending_courses if c["course_code"] == "CMSC132")
    phys = next(c for c in pending_courses if c["course_code"] == "PHYS260")

    decide_resp = await client.post(
        "/visibility/decide",
        json={
            "decisions": [
                {"course_id": cmsc["course_id"], "group_id": cmsc["groups"][0]["group_id"], "visible": True},
                {"course_id": phys["course_id"], "group_id": phys["groups"][0]["group_id"], "visible": False},
            ]
        },
        headers=auth_headers,
    )
    assert decide_resp.status_code == 200

    # Pending should be empty
    pending_after = await client.get("/visibility/pending", headers=auth_headers)
    assert len(pending_after.json()["pending"]) == 0

    # --- Step 6: User2 views progress ---
    progress_resp = await client.get(f"/groups/{group_id}/progress", headers=auth_headers2)
    assert progress_resp.status_code == 200
    progress = progress_resp.json()
    assert progress["group_name"] == "CMSC132 Study Group"

    user1_progress = next(m for m in progress["members"] if m["username"] == "testuser")
    assert len(user1_progress["courses"]) == 1  # Only CMSC132 visible
    assert user1_progress["courses"][0]["course_code"] == "CMSC132"
    assert len(user1_progress["courses"][0]["assignments"]) == 2

    hw1 = next(a for a in user1_progress["courses"][0]["assignments"] if a["name"] == "HW 1")
    assert hw1["status"] == "submitted"
    hw2 = next(a for a in user1_progress["courses"][0]["assignments"] if a["name"] == "HW 2")
    assert hw2["status"] == "unsubmitted"

    # User2 has no synced courses
    user2_progress = next(m for m in progress["members"] if m["username"] == "otheruser")
    assert len(user2_progress["courses"]) == 0

    # --- Step 7: User1 syncs again with updates ---
    sync2_resp = await client.post("/sync", json=UPDATED_SYNC, headers=auth_headers)
    assert sync2_resp.status_code == 200
    # No new courses, so no new visibility prompts
    assert len(sync2_resp.json()["new_courses_needing_visibility"]) == 0

    # --- Step 8: User2 checks updated progress ---
    progress2 = await client.get(f"/groups/{group_id}/progress", headers=auth_headers2)
    user1_updated = next(m for m in progress2.json()["members"] if m["username"] == "testuser")
    assignments = {a["name"]: a for a in user1_updated["courses"][0]["assignments"]}
    assert assignments["HW 1"]["status"] == "graded"
    assert assignments["HW 2"]["status"] == "submitted"

    # PHYS260 still hidden
    assert len(user1_updated["courses"]) == 1

    # --- Step 9: Transfer leadership ---
    xfer_resp = await client.post(
        f"/groups/{group_id}/transfer-leadership",
        json={"new_leader_id": str(test_user2.id)},
        headers=auth_headers,
    )
    assert xfer_resp.status_code == 200

    detail2 = await client.get(f"/groups/{group_id}", headers=auth_headers2)
    assert detail2.json()["leader"]["username"] == "otheruser"

    # --- Step 10: User2 (new leader) renames group ---
    rename_resp = await client.patch(
        f"/groups/{group_id}", json={"name": "CS Study Squad"}, headers=auth_headers2
    )
    assert rename_resp.status_code == 200
    assert rename_resp.json()["name"] == "CS Study Squad"

    # User1 (no longer leader) can't rename
    bad_rename = await client.patch(
        f"/groups/{group_id}", json={"name": "Nope"}, headers=auth_headers
    )
    assert bad_rename.status_code == 403

    # --- Step 11: User1 leaves ---
    leave_resp = await client.delete(f"/groups/{group_id}/leave", headers=auth_headers)
    assert leave_resp.status_code == 200

    # User1 no longer in group
    groups_list = await client.get("/groups", headers=auth_headers)
    assert len(groups_list.json()) == 0

    # User2 still in group
    detail_final = await client.get(f"/groups/{group_id}", headers=auth_headers2)
    assert len(detail_final.json()["members"]) == 1
