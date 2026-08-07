"""Tests for plan-based feature gating (Starter / Growth / Pro)."""
import pytest


async def _login(client, role: str, plan: str = "starter") -> dict:
    resp = await client.post(f"/api/auth/demo?role={role}&plan={plan}")
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _checkout(**overrides):
    payload = {
        "payment_method": "cod",
        "recipient_name": "Test Buyer",
        "recipient_phone": "+85512345678",
        "delivery_address": "123 Street, Phnom Penh",
        "delivery_note": "",
    }
    payload.update(overrides)
    return payload


async def _mk_product(client, auth, name="Widget", **overrides):
    payload = {"name": name, "price": 20, "stock": 10}
    payload.update(overrides)
    resp = await client.post("/api/admin/products", json=payload, headers=auth)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Plan exposed to clients ------------------------------------------------


async def test_auth_response_includes_plan(client):
    resp = await client.post("/api/auth/demo?role=admin&plan=growth")
    assert resp.status_code == 200
    assert resp.json()["user"]["plan"] == "growth"

    resp = await client.post("/api/auth/demo?role=buyer")
    assert resp.json()["user"]["plan"] == "starter"


async def test_store_payload_exposes_plan_and_features(client):
    await _login(client, "admin", "starter")
    body = (await client.get("/api/store")).json()
    assert body["plan"] == "starter"
    assert body["features"]["coupons"] is False
    assert body["features"]["online_payments"] is False
    assert body["features"]["analytics"] is False
    assert body["online_payments_enabled"] is False

    await _login(client, "admin", "pro")
    body = (await client.get("/api/store")).json()
    assert body["plan"] == "pro"
    assert body["features"]["coupons"] is True
    assert body["features"]["online_payments"] is True
    assert body["features"]["analytics"] is True


# --- Coupons are Growth+ ----------------------------------------------------


async def test_starter_admin_cannot_create_coupon(client):
    auth = await _login(client, "admin", "starter")
    resp = await client.post(
        "/api/admin/coupons",
        json={"code": "SAVE10", "discount_type": "percent", "value": 10},
        headers=auth,
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "plan_required"


async def test_growth_admin_can_create_coupon(client):
    auth = await _login(client, "admin", "growth")
    resp = await client.post(
        "/api/admin/coupons",
        json={"code": "SAVE10", "discount_type": "percent", "value": 10},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text


async def test_starter_admin_coupon_list_403(client):
    auth = await _login(client, "admin", "starter")
    resp = await client.get("/api/admin/coupons", headers=auth)
    assert resp.status_code == 403
    assert resp.json()["code"] == "plan_required"


async def test_buyer_coupon_check_blocked_on_starter_store(client):
    await _login(client, "admin", "starter")
    buyer = await _login(client, "buyer")
    resp = await client.post("/api/coupons/check", json={"code": "SAVE10"}, headers=buyer)
    assert resp.status_code == 403
    assert resp.json()["code"] == "plan_required"


async def test_checkout_with_coupon_blocked_on_starter_store(client):
    auth = await _login(client, "admin", "starter")
    prod = await _mk_product(client, auth)
    buyer = await _login(client, "buyer")
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 1}, headers=buyer
    )
    resp = await client.post(
        "/api/orders/checkout", json=_checkout(coupon_code="SAVE10"), headers=buyer
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "plan_required"


# --- Online payments are Growth+ --------------------------------------------


async def test_online_checkout_blocked_on_starter(client):
    auth = await _login(client, "admin", "starter")
    prod = await _mk_product(client, auth)
    buyer = await _login(client, "buyer")
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 1}, headers=buyer
    )
    resp = await client.post(
        "/api/orders/checkout", json=_checkout(payment_method="online"), headers=buyer
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "plan_required"


async def test_starter_admin_cannot_enable_online_payments(client):
    auth = await _login(client, "admin", "starter")
    resp = await client.patch(
        "/api/admin/settings", json={"online_payments_enabled": True}, headers=auth
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "plan_required"


async def test_growth_admin_can_enable_online_payments(client):
    auth = await _login(client, "admin", "growth")
    resp = await client.patch(
        "/api/admin/settings", json={"online_payments_enabled": True}, headers=auth
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["online_payments_enabled"] is True


# --- Product quota (Starter = 50) --------------------------------------------


async def test_starter_product_quota_enforced(client):
    auth = await _login(client, "admin", "starter")
    for i in range(50):
        resp = await client.post(
            "/api/admin/products", json={"name": f"P{i}", "price": 1, "stock": 1}, headers=auth
        )
        assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/api/admin/products", json={"name": "Overflow", "price": 1, "stock": 1}, headers=auth
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "plan_limit"


async def test_csv_import_over_quota_rejected(client):
    auth = await _login(client, "admin", "starter")
    rows = "\n".join(f"Bulk{i},5,10,SKU-{i}" for i in range(51))
    csv_data = f"name,price,stock,sku\n{rows}\n"
    resp = await client.post(
        "/api/admin/products/import",
        files={"file": ("bulk.csv", csv_data.encode(), "text/csv")},
        headers=auth,
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "plan_limit"

    # nothing was imported
    resp = await client.get("/api/admin/products", headers=auth)
    assert resp.json()["total"] == 0


async def test_pro_products_unlimited(client):
    auth = await _login(client, "admin", "pro")
    for i in range(60):
        resp = await client.post(
            "/api/admin/products", json={"name": f"Pro{i}", "price": 1, "stock": 1}, headers=auth
        )
        assert resp.status_code == 200, resp.text


# --- Dashboard analytics redaction ------------------------------------------


async def test_dashboard_advanced_redacted_on_starter(client):
    auth = await _login(client, "admin", "starter")
    body = (await client.get("/api/admin/dashboard", headers=auth)).json()
    assert body["sales_last_14_days"] == []
    assert body["top_products"] == []
    assert body["revenue_by_category"] == []
    assert body["coupon_redemptions"] == []
    assert float(body["avg_order_value"]) == 0
    assert body["repeat_customer_rate"] == 0.0
    # basic KPIs stay
    assert "total_orders" in body


async def test_dashboard_advanced_present_on_pro(client):
    auth = await _login(client, "admin", "pro")
    body = (await client.get("/api/admin/dashboard", headers=auth)).json()
    assert len(body["sales_last_14_days"]) == 14
    assert body["top_products"] == []
    assert "revenue_by_category" in body
