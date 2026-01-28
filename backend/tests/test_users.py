import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers: dict, test_user: User):
    resp = await client.get("/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["discriminator"] == "0001"
    assert data["id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    resp = await client.get("/users/me")
    assert resp.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_update_username(client: AsyncClient, auth_headers: dict):
    resp = await client.patch("/users/me", json={"username": "newname"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "newname"


@pytest.mark.asyncio
async def test_update_username_empty_rejected(client: AsyncClient, auth_headers: dict):
    resp = await client.patch("/users/me", json={"username": ""}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_users(client: AsyncClient, auth_headers: dict, test_user: User):
    resp = await client.get("/users/search?q=test", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["username"] == "testuser"


@pytest.mark.asyncio
async def test_search_users_too_short(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/users/search?q=a", headers=auth_headers)
    assert resp.status_code == 400
