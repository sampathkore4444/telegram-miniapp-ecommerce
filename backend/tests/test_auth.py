import pytest

from app.api.auth import _demo_login_allowed_for
from app.core.config import settings
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


async def test_security_headers_present(client):
    resp = await client.get("/api/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "SAMEORIGIN"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    csp = resp.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self' https://telegram.org" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'self'" in csp


async def test_demo_login_blocked_in_production(client, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "DEBUG", False)
    resp = await client.post("/api/auth/demo?role=admin")
    assert resp.status_code == 400
    assert resp.json()["code"] == "demo_disabled"


async def test_demo_login_blocked_in_deployed_development(monkeypatch):
    """APP_ENV=development with DEBUG=false (a deployed dev image) must not
    expose the demo admin login, even though is_dev() is technically true."""
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEBUG", False)
    assert _demo_login_allowed_for("203.0.113.9") is False


async def test_demo_login_allowed_when_debug(client, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEBUG", True)
    resp = await client.post("/api/auth/demo?role=admin")
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "admin"


async def test_demo_login_allowed_from_loopback(client, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEBUG", False)
    assert _demo_login_allowed_for("127.0.0.1") is True
    assert _demo_login_allowed_for("::1") is True
