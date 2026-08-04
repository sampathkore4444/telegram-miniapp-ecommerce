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


async def _prime_cart(client, auth, catalog, qty=1):
    pid = catalog["product"]["id"]
    await client.post("/api/cart/add", json={"product_id": pid, "quantity": qty}, headers=auth)


async def test_checkout_cod(client, buyer_auth, catalog):
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post("/api/orders/checkout", json=_checkout_payload(), headers=buyer_auth)
    assert resp.status_code == 200, resp.text
    order = resp.json()
    assert order["status"] == "pending"
    assert order["payment_method"] == "cod"
    assert order["total"] == 100.0
    assert order["order_number"].startswith("ORD-")
    assert order["payment_status"] == "unpaid"

    # stock decremented
    prod = await client.get(f"/api/products/{catalog['product']['id']}")
    assert prod.json()["stock"] == 9


async def test_checkout_empty_cart_rejected(client, buyer_auth):
    resp = await client.post("/api/orders/checkout", json=_checkout_payload(), headers=buyer_auth)
    assert resp.status_code == 400
    assert resp.json()["code"] == "empty_cart"


async def test_checkout_qr_flow(client, buyer_auth, catalog):
    await _prime_cart(client, buyer_auth, catalog)
    resp = await client.post(
        "/api/orders/checkout", json=_checkout_payload(payment_method="bank_qr"), headers=buyer_auth
    )
    assert resp.status_code == 200, resp.text
    order = resp.json()
    assert order["status"] == "pending_payment"
    assert order["payment_method"] == "bank_qr"


async def test_submit_payment_proof_then_admin_verifies(client, buyer_auth, admin_auth, catalog):
    await _prime_cart(client, buyer_auth, catalog)
    order = (
        await client.post(
            "/api/orders/checkout",
            json=_checkout_payload(payment_method="bank_qr"),
            headers=buyer_auth,
        )
    ).json()
    oid = order["id"]

    proof = await client.post(
        f"/api/orders/{oid}/payment-proof",
        data={"transaction_ref": "REF-12345"},
        headers=buyer_auth,
    )
    assert proof.status_code == 200, proof.text
    assert proof.json()["status"] == "under_review"

    verify = await client.patch(
        f"/api/admin/orders/{oid}/status",
        json={"status": "confirmed", "note": "Payment verified"},
        headers=admin_auth,
    )
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["status"] == "confirmed"
    assert body["payment_status"] == "paid"
    assert body["paid_at"] is not None


async def test_admin_verifies_cod(client, buyer_auth, admin_auth, catalog):
    await _prime_cart(client, buyer_auth, catalog)
    order = (await client.post("/api/orders/checkout", json=_checkout_payload(), headers=buyer_auth)).json()
    oid = order["id"]

    resp = await client.patch(
        f"/api/admin/orders/{oid}/status", json={"status": "confirmed"}, headers=admin_auth
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


async def test_full_delivery_flow(client, buyer_auth, admin_auth, catalog):
    await _prime_cart(client, buyer_auth, catalog)
    order = (await client.post("/api/orders/checkout", json=_checkout_payload(), headers=buyer_auth)).json()
    oid = order["id"]
    for status in ("confirmed", "processing", "shipped", "delivered", "completed"):
        resp = await client.patch(
            f"/api/admin/orders/{oid}/status", json={"status": status}, headers=admin_auth
        )
        assert resp.status_code == 200, resp.text
    final = (await client.get(f"/api/orders/{oid}", headers=buyer_auth)).json()
    assert final["status"] == "completed"
    assert final["payment_status"] == "paid"
    assert len(final["status_logs"]) == 6


async def test_buyer_cannot_access_other_order(client, buyer_auth, admin_auth, catalog):
    await _prime_cart(client, buyer_auth, catalog)
    order = (await client.post("/api/orders/checkout", json=_checkout_payload(), headers=buyer_auth)).json()

    # Create a second, distinct buyer directly and prove the endpoint is scoped.
    from app.core.security import create_access_token
    from app.db.session import AsyncSessionLocal
    from app.models import User

    async with AsyncSessionLocal() as db:
        db.add(User(telegram_id=555001, username="other", first_name="Other", last_name="Buyer"))
        await db.commit()
        other_id = (
            (await db.execute(__import__("sqlalchemy").select(User).where(User.telegram_id == 555001)))
            .scalar_one()
            .id
        )
    other = {"Authorization": f"Bearer {create_access_token(other_id, 'buyer')}"}

    resp = await client.get(f"/api/orders/{order['id']}", headers=other)
    assert resp.status_code == 404


async def test_cancel_order_restocks(client, buyer_auth, catalog):
    await _prime_cart(client, buyer_auth, catalog)
    order = (await client.post("/api/orders/checkout", json=_checkout_payload(), headers=buyer_auth)).json()
    oid = order["id"]
    resp = await client.post(f"/api/orders/{oid}/cancel", headers=buyer_auth)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    prod = await client.get(f"/api/products/{catalog['product']['id']}")
    assert prod.json()["stock"] == 10


async def test_cancel_non_cancellable_rejected(client, buyer_auth, admin_auth, catalog):
    await _prime_cart(client, buyer_auth, catalog)
    order = (await client.post("/api/orders/checkout", json=_checkout_payload(), headers=buyer_auth)).json()
    oid = order["id"]
    await client.patch(f"/api/admin/orders/{oid}/status", json={"status": "confirmed"}, headers=admin_auth)
    resp = await client.post(f"/api/orders/{oid}/cancel", headers=buyer_auth)
    assert resp.status_code == 400
