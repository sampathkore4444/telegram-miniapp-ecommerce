"""Multi-store tests: store CRUD, Pro multi-store gating, per-store scoping.

Covers the new ``/admin/stores`` router and the ``X-Store-Slug`` header that
routes both public and admin requests to a specific store.
"""
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models import User, UserRole


async def _login(client, role="admin", plan="starter"):
    resp = await client.post(f"/api/auth/demo?role={role}&plan={plan}")
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def _h(auth, slug=None):
    headers = dict(auth)
    if slug:
        headers["X-Store-Slug"] = slug
    return headers


async def _mk_product(client, auth, name="Widget", price=20, headers=None, **overrides):
    payload = {"name": name, "price": price, "stock": 10}
    payload.update(overrides)
    request_headers = dict(auth)
    if headers:
        request_headers.update(headers)
    resp = await client.post("/api/admin/products", json=payload, headers=request_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _mk_admin(telegram_id: int, username: str, plan: str) -> dict:
    async with AsyncSessionLocal() as db:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=username,
            role=UserRole.ADMIN,
            plan=plan,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {"Authorization": f"Bearer {create_access_token(user.id, 'admin')}"}


# --- Store CRUD --------------------------------------------------------------


async def test_admin_has_primary_store_after_login(client):
    auth = await _login(client, "admin", "starter")
    resp = await client.get("/api/admin/stores", headers=auth)
    assert resp.status_code == 200, resp.text
    stores = resp.json()
    assert len(stores) == 1
    assert stores[0]["plan"] == "starter"
    assert stores[0]["slug"]
    assert "features" in stores[0]
    assert stores[0]["product_count"] == 0


async def test_first_store_create_allowed_on_any_plan(client):
    auth = await _mk_admin(888, "newbie", "starter")
    resp = await client.post(
        "/api/admin/stores", json={"name": "My First Shop"}, headers=auth
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["slug"] == "my-first-shop"
    stores = (await client.get("/api/admin/stores", headers=auth)).json()
    assert len(stores) == 1


async def test_second_store_requires_multi_store(client):
    for plan in ("starter", "growth"):
        auth = await _login(client, "admin", plan)
        resp = await client.post(
            "/api/admin/stores", json={"name": "Second"}, headers=auth
        )
        assert resp.status_code == 403, resp.text
        assert resp.json()["code"] == "plan_required"


async def test_pro_can_create_second_store(client):
    auth = await _login(client, "admin", "pro")
    resp = await client.post(
        "/api/admin/stores", json={"name": "Second"}, headers=auth
    )
    assert resp.status_code == 200, resp.text
    stores = (await client.get("/api/admin/stores", headers=auth)).json()
    assert len(stores) == 2


async def test_store_slugs_unique_across_stores(client):
    auth = await _login(client, "admin", "pro")
    s2 = (
        await client.post(
            "/api/admin/stores", json={"name": "My Shop"}, headers=auth
        )
    ).json()
    s3 = (
        await client.post(
            "/api/admin/stores", json={"name": "My Shop"}, headers=auth
        )
    ).json()
    assert s2["slug"] == "my-shop"
    assert s3["slug"] == "my-shop-2"


async def test_store_update_and_deactivate(client):
    auth = await _login(client, "admin", "pro")
    s1 = (await client.get("/api/admin/stores", headers=auth)).json()[0]
    resp = await client.patch(
        f"/api/admin/stores/{s1['id']}",
        json={"name": "Renamed", "is_active": False},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Renamed"
    assert resp.json()["is_active"] is False

    buyer = await _login(client, "buyer")
    resp = await client.get("/api/products", headers=_h(buyer, s1["slug"]))
    assert resp.status_code == 404
    assert resp.json()["code"] == "store_not_found"


async def test_delete_empty_store(client):
    auth = await _login(client, "admin", "pro")
    s2 = (
        await client.post(
            "/api/admin/stores", json={"name": "Empty"}, headers=auth
        )
    ).json()
    resp = await client.delete(f"/api/admin/stores/{s2['id']}", headers=auth)
    assert resp.status_code == 204, resp.text
    stores = (await client.get("/api/admin/stores", headers=auth)).json()
    assert len(stores) == 1


async def test_delete_store_with_data_conflicts(client):
    auth = await _login(client, "admin", "pro")
    s2 = (
        await client.post(
            "/api/admin/stores", json={"name": "Busy"}, headers=auth
        )
    ).json()
    await _mk_product(client, auth, name="Busy Product", headers=_h(auth, s2["slug"]))
    resp = await client.delete(f"/api/admin/stores/{s2['id']}", headers=auth)
    assert resp.status_code == 409
    assert resp.json()["code"] == "conflict"


async def test_unknown_store_slug_404(client):
    buyer = await _login(client, "buyer")
    resp = await client.get("/api/products", headers=_h(buyer, "no-such-store"))
    assert resp.status_code == 404
    assert resp.json()["code"] == "store_not_found"


async def test_admin_cannot_operate_other_admins_store(client):
    auth = await _login(client, "admin", "pro")
    s1 = (await client.get("/api/admin/stores", headers=auth)).json()[0]
    other = await _mk_admin(999, "other_admin", "pro")
    resp = await client.get("/api/admin/products", headers=_h(other, s1["slug"]))
    assert resp.status_code == 403
    assert resp.json()["code"] == "store_forbidden"


# --- Per-store scoping --------------------------------------------------------


async def test_products_scoped_per_store(client):
    admin = await _login(client, "admin", "pro")
    s1 = (await client.get("/api/admin/stores", headers=admin)).json()[0]
    s2 = (
        await client.post(
            "/api/admin/stores", json={"name": "Second"}, headers=admin
        )
    ).json()

    p1 = await _mk_product(
        client, admin, name="Shared Slug", headers=_h(admin, s1["slug"])
    )
    p2 = await _mk_product(
        client, admin, name="Shared Slug", headers=_h(admin, s2["slug"])
    )
    assert p1["id"] != p2["id"]
    assert p1["slug"] == p2["slug"]

    l1 = (await client.get("/api/admin/products", headers=_h(admin, s1["slug"]))).json()
    l2 = (await client.get("/api/admin/products", headers=_h(admin, s2["slug"]))).json()
    assert [p["id"] for p in l1["items"]] == [p1["id"]]
    assert [p["id"] for p in l2["items"]] == [p2["id"]]

    buyer = await _login(client, "buyer")
    b1 = (await client.get("/api/products", headers=_h(buyer, s1["slug"]))).json()
    b2 = (await client.get("/api/products", headers=_h(buyer, s2["slug"]))).json()
    assert [p["id"] for p in b1["items"]] == [p1["id"]]
    assert [p["id"] for p in b2["items"]] == [p2["id"]]

    # store payload matches the selected store
    body = (await client.get("/api/store", headers=_h(buyer, s2["slug"]))).json()
    assert body["store"]["slug"] == s2["slug"]


async def test_cart_scoped_per_store(client):
    admin = await _login(client, "admin", "pro")
    s1 = (await client.get("/api/admin/stores", headers=admin)).json()[0]
    s2 = (
        await client.post(
            "/api/admin/stores", json={"name": "Second"}, headers=admin
        )
    ).json()
    p1 = await _mk_product(client, admin, headers=_h(admin, s1["slug"]))
    p2 = await _mk_product(client, admin, headers=_h(admin, s2["slug"]))

    buyer = await _login(client, "buyer")
    await client.post(
        "/api/cart/add",
        json={"product_id": p1["id"], "quantity": 1},
        headers=_h(buyer, s1["slug"]),
    )
    await client.post(
        "/api/cart/add",
        json={"product_id": p2["id"], "quantity": 1},
        headers=_h(buyer, s2["slug"]),
    )
    cart1 = (await client.get("/api/cart", headers=_h(buyer, s1["slug"]))).json()
    cart2 = (await client.get("/api/cart", headers=_h(buyer, s2["slug"]))).json()
    assert [i["product"]["id"] for i in cart1["items"]] == [p1["id"]]
    assert [i["product"]["id"] for i in cart2["items"]] == [p2["id"]]
    assert cart1["item_count"] == 1
    assert cart2["item_count"] == 1


async def test_product_slug_collision_across_stores_allowed(client):
    admin = await _login(client, "admin", "pro")
    s2 = (
        await client.post(
            "/api/admin/stores", json={"name": "Second"}, headers=admin
        )
    ).json()
    p1 = await _mk_product(client, admin, name="Widget", headers=_h(admin, None))
    p2 = await _mk_product(client, admin, name="Widget", headers=_h(admin, s2["slug"]))
    assert p1["slug"] == p2["slug"] == "widget"
    assert p1["id"] != p2["id"]


# --- Public store directory ---------------------------------------------------


async def test_public_directory_no_auth(client):
    resp = await client.get("/api/stores")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_public_directory_lists_active_stores_with_payload(client):
    admin = await _login(client, "admin", "pro")
    s2 = (
        await client.post(
            "/api/admin/stores", json={"name": "Second Shop"}, headers=admin
        )
    ).json()
    await _mk_product(client, admin, name="Widget", headers=_h(admin, s2["slug"]))

    resp = await client.get("/api/stores")
    assert resp.status_code == 200, resp.text
    stores = resp.json()
    slugs = {s["slug"] for s in stores}
    assert s2["slug"] in slugs
    for s in stores:
        assert set(s) == set(
            ("id", "name", "slug", "store_name", "description", "product_count", "plan")
        )
        assert "is_active" not in s and "features" not in s

    # stores with more products sort first
    by_slug = {s["slug"]: s for s in stores}
    assert by_slug[s2["slug"]]["product_count"] == 1


async def test_public_directory_excludes_inactive_stores(client):
    admin = await _login(client, "admin", "pro")
    s1 = (await client.get("/api/admin/stores", headers=admin)).json()[0]
    await client.patch(
        f"/api/admin/stores/{s1['id']}", json={"is_active": False}, headers=admin
    )
    resp = await client.get("/api/stores")
    slugs = {s["slug"] for s in resp.json()}
    assert s1["slug"] not in slugs
