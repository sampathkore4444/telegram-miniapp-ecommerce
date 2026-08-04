import pytest

from app.core.telegram import extract_user, validate_init_data


async def test_demo_login_buyer(client):
    resp = await client.post("/api/auth/demo?role=buyer")
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]
    assert data["user"]["role"] == "buyer"
    assert data["user"]["telegram_id"] == 2


async def test_demo_login_admin(client):
    resp = await client.post("/api/auth/demo?role=admin")
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "admin"


async def test_profile_endpoint(client, buyer_auth):
    resp = await client.get("/api/me", headers=buyer_auth)
    assert resp.status_code == 200
    assert resp.json()["role"] == "buyer"


async def test_profile_update(client, buyer_auth):
    resp = await client.patch(
        "/api/me", json={"phone": "+85512345678", "address": "Phnom Penh"}, headers=buyer_auth
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == "+85512345678"


async def test_telegram_login_rejects_bad_init_data(client):
    resp = await client.post("/api/auth/telegram", json={"init_data": "query_id=abc&hash=bad"})
    assert resp.status_code == 401


async def test_unauthorized_access(client):
    resp = await client.get("/api/me")
    assert resp.status_code == 403


async def test_admin_guard(client, buyer_auth):
    resp = await client.get("/api/admin/dashboard", headers=buyer_auth)
    assert resp.status_code == 403


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
