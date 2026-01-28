import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_group(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/groups", json={"name": "Study Group"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Study Group"
    assert data["is_leader"] is True
    assert data["member_count"] == 1
    assert len(data["invite_code"]) == 8


@pytest.mark.asyncio
async def test_list_groups(client: AsyncClient, auth_headers: dict):
    await client.post("/groups", json={"name": "Group A"}, headers=auth_headers)
    await client.post("/groups", json={"name": "Group B"}, headers=auth_headers)
    resp = await client.get("/groups", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_group_detail(client: AsyncClient, auth_headers: dict, test_user: User):
    create_resp = await client.post("/groups", json={"name": "Detail Group"}, headers=auth_headers)
    group_id = create_resp.json()["id"]

    resp = await client.get(f"/groups/{group_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail Group"
    assert data["leader"]["username"] == "testuser"
    assert len(data["members"]) == 1


@pytest.mark.asyncio
async def test_update_group_leader_only(
    client: AsyncClient, auth_headers: dict, auth_headers2: dict, test_user2: User
):
    create_resp = await client.post("/groups", json={"name": "My Group"}, headers=auth_headers)
    group = create_resp.json()

    # Join as user2
    await client.post("/groups/join", json={"invite_code": group["invite_code"]}, headers=auth_headers2)

    # User2 cannot update
    resp = await client.patch(f"/groups/{group['id']}", json={"name": "Hacked"}, headers=auth_headers2)
    assert resp.status_code == 403

    # Leader can update
    resp = await client.patch(f"/groups/{group['id']}", json={"name": "Renamed"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


@pytest.mark.asyncio
async def test_join_group_via_invite(client: AsyncClient, auth_headers: dict, auth_headers2: dict):
    create_resp = await client.post("/groups", json={"name": "Join Test"}, headers=auth_headers)
    invite_code = create_resp.json()["invite_code"]

    resp = await client.post("/groups/join", json={"invite_code": invite_code}, headers=auth_headers2)
    assert resp.status_code == 200
    assert resp.json()["member_count"] == 2


@pytest.mark.asyncio
async def test_join_group_invalid_code(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/groups/join", json={"invite_code": "XXXXXXXX"}, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_join_group_duplicate(client: AsyncClient, auth_headers: dict, auth_headers2: dict):
    create_resp = await client.post("/groups", json={"name": "Dup Test"}, headers=auth_headers)
    invite = create_resp.json()["invite_code"]

    await client.post("/groups/join", json={"invite_code": invite}, headers=auth_headers2)
    resp = await client.post("/groups/join", json={"invite_code": invite}, headers=auth_headers2)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_leave_group(client: AsyncClient, auth_headers: dict, auth_headers2: dict):
    create_resp = await client.post("/groups", json={"name": "Leave Test"}, headers=auth_headers)
    group = create_resp.json()

    await client.post("/groups/join", json={"invite_code": group["invite_code"]}, headers=auth_headers2)

    resp = await client.delete(f"/groups/{group['id']}/leave", headers=auth_headers2)
    assert resp.status_code == 200

    # Verify member count
    detail = await client.get(f"/groups/{group['id']}", headers=auth_headers)
    assert len(detail.json()["members"]) == 1


@pytest.mark.asyncio
async def test_leader_leave_transfers_leadership(client: AsyncClient, auth_headers: dict, auth_headers2: dict):
    create_resp = await client.post("/groups", json={"name": "Transfer Test"}, headers=auth_headers)
    group = create_resp.json()

    await client.post("/groups/join", json={"invite_code": group["invite_code"]}, headers=auth_headers2)

    # Leader leaves
    resp = await client.delete(f"/groups/{group['id']}/leave", headers=auth_headers)
    assert resp.status_code == 200

    # User2 should now be leader
    detail = await client.get(f"/groups/{group['id']}", headers=auth_headers2)
    assert detail.status_code == 200
    assert detail.json()["leader"]["username"] == "otheruser"


@pytest.mark.asyncio
async def test_last_member_leave_deletes_group(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/groups", json={"name": "Delete Test"}, headers=auth_headers)
    group = create_resp.json()

    resp = await client.delete(f"/groups/{group['id']}/leave", headers=auth_headers)
    assert resp.status_code == 200

    # Group should be gone
    detail = await client.get(f"/groups/{group['id']}", headers=auth_headers)
    assert detail.status_code in (403, 404)


@pytest.mark.asyncio
async def test_delete_group_leader_only(client: AsyncClient, auth_headers: dict, auth_headers2: dict):
    create_resp = await client.post("/groups", json={"name": "Del Group"}, headers=auth_headers)
    group = create_resp.json()

    await client.post("/groups/join", json={"invite_code": group["invite_code"]}, headers=auth_headers2)

    resp = await client.delete(f"/groups/{group['id']}", headers=auth_headers2)
    assert resp.status_code == 403

    resp = await client.delete(f"/groups/{group['id']}", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_remove_member(client: AsyncClient, auth_headers: dict, auth_headers2: dict, test_user2: User):
    create_resp = await client.post("/groups", json={"name": "Remove Test"}, headers=auth_headers)
    group = create_resp.json()

    await client.post("/groups/join", json={"invite_code": group["invite_code"]}, headers=auth_headers2)

    resp = await client.delete(f"/groups/{group['id']}/members/{test_user2.id}", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_transfer_leadership(client: AsyncClient, auth_headers: dict, auth_headers2: dict, test_user2: User):
    create_resp = await client.post("/groups", json={"name": "XFer Test"}, headers=auth_headers)
    group = create_resp.json()

    await client.post("/groups/join", json={"invite_code": group["invite_code"]}, headers=auth_headers2)

    resp = await client.post(
        f"/groups/{group['id']}/transfer-leadership",
        json={"new_leader_id": str(test_user2.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    detail = await client.get(f"/groups/{group['id']}", headers=auth_headers2)
    assert detail.json()["leader"]["username"] == "otheruser"


@pytest.mark.asyncio
async def test_regenerate_invite(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/groups", json={"name": "Regen Test"}, headers=auth_headers)
    group = create_resp.json()
    old_code = group["invite_code"]

    resp = await client.post(f"/groups/{group['id']}/regenerate-invite", headers=auth_headers)
    assert resp.status_code == 200
    new_code = resp.json()["invite_code"]
    assert new_code != old_code
    assert len(new_code) == 8
