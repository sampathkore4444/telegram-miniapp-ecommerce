import pytest


def _checkout_payload(**overrides):
    payload = {
        "payment_method": "cod",
        "recipient_name": "Test Buyer",
        "recipient_phone": "+85512345678",
        "delivery_address": "123 Street, Phnom Penh",
        "delivery_note": "",
    }
    payload.update(overrides)
    return payload


async def _prime_cart(client, buyer_auth, catalog, qty=1):
    pid = catalog["product"]["id"]
    await client.post("/api/cart/add", json={"product_id": pid, "quantity": qty}, headers=buyer_auth)


async def _create_coupon(client, admin_auth, **overrides):
    payload = {
        "code": "SAVE10",
        "discount_type": "percent",
        "value": 10,
        "min_subtotal": 0,
        "max_uses": None,
        "per_user_limit": 1,
        "is_active": True,
    }
    payload.update(overrides)
    resp = await client.post("/api/admin/coupons", json=payload, headers=admin_auth)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_admin_create_coupon(client, admin_auth):
    coupon = await _create_coupon(client, admin_auth)
    assert coupon["code"] == "SAVE10"
    assert coupon["value"] == 10.0


async def test_admin_duplicate_code_rejected(client, admin_auth):
    await _create_coupon(client, admin_auth)
    resp = await client.post(
        "/api/admin/coupons",
        json={"code": "save10", "discount_type": "percent", "value": 20},
        headers=admin_auth,
    )
    assert resp.status_code == 409


async def test_checkout_with_percent_coupon(client, buyer_auth, admin_auth, catalog):
    await _create_coupon(client, admin_auth)
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post(
        "/api/orders/checkout", json=_checkout_payload(coupon_code="save10"), headers=buyer_auth
    )
    assert resp.status_code == 200, resp.text
    order = resp.json()
    assert order["discount"] == 10.0
    assert order["total"] == 90.0
    assert order["coupon_code"] == "SAVE10"


async def test_checkout_with_fixed_coupon(client, buyer_auth, admin_auth, catalog):
    await _create_coupon(client, admin_auth, code="FIX5", discount_type="fixed", value=5)
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post(
        "/api/orders/checkout", json=_checkout_payload(coupon_code="FIX5"), headers=buyer_auth
    )
    assert resp.status_code == 200, resp.text
    order = resp.json()
    assert order["discount"] == 5.0
    assert order["total"] == 95.0


async def test_invalid_coupon_rejected(client, buyer_auth, admin_auth, catalog):
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post(
        "/api/orders/checkout", json=_checkout_payload(coupon_code="NOPE"), headers=buyer_auth
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "coupon_not_found"


async def test_coupon_min_subtotal_rejected(client, buyer_auth, admin_auth, catalog):
    await _create_coupon(client, admin_auth, min_subtotal=200)
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post(
        "/api/orders/checkout", json=_checkout_payload(coupon_code="SAVE10"), headers=buyer_auth
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "coupon_min_subtotal"


async def test_coupon_global_usage_limit(client, buyer_auth, admin_auth, catalog):
    await _create_coupon(client, admin_auth, max_uses=1, per_user_limit=2)
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post(
        "/api/orders/checkout", json=_checkout_payload(coupon_code="SAVE10"), headers=buyer_auth
    )
    assert resp.status_code == 200, resp.text
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post(
        "/api/orders/checkout", json=_checkout_payload(coupon_code="SAVE10"), headers=buyer_auth
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "coupon_used_up"


async def test_coupon_per_user_limit(client, buyer_auth, admin_auth, catalog):
    await _create_coupon(client, admin_auth, per_user_limit=1, max_uses=10)
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post(
        "/api/orders/checkout", json=_checkout_payload(coupon_code="SAVE10"), headers=buyer_auth
    )
    assert resp.status_code == 200, resp.text
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post(
        "/api/orders/checkout", json=_checkout_payload(coupon_code="SAVE10"), headers=buyer_auth
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "coupon_used_by_user"


async def test_coupon_check_endpoint(client, buyer_auth, admin_auth, catalog):
    await _create_coupon(client, admin_auth)
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post("/api/coupons/check", json={"code": "save10"}, headers=buyer_auth)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == "SAVE10"
    assert body["discount_amount"] == 10.0
