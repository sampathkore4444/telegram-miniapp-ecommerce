"""Tests for feature batch 2: online payments, tracking, CSV exports,
saved addresses, recently viewed, broadcasts and admin low-stock alerts."""

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models import User


async def _other_buyer_auth() -> dict:
    """Demo login always reuses telegram_id 2, so create a distinct buyer directly."""
    async with AsyncSessionLocal() as db:
        user = User(telegram_id=999999, username="other_buyer", first_name="Other")
        db.add(user)
        await db.commit()
        token = create_access_token(user.id, "buyer")
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


async def _mk_product(client, admin_auth, **overrides):
    payload = {"name": "Widget", "price": 20, "stock": 10}
    payload.update(overrides)
    resp = await client.post("/api/admin/products", json=payload, headers=admin_auth)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Online payments (sandbox gateway) -------------------------------------


async def test_online_checkout_creates_pending_payment(client, buyer_auth, admin_auth):
    prod = await _mk_product(client, admin_auth, name="OnlineItem", price=30, stock=5)
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 1}, headers=buyer_auth
    )
    order = (
        await client.post(
            "/api/orders/checkout", json=_checkout(payment_method="online"), headers=buyer_auth
        )
    ).json()
    assert order["status"] == "pending_payment"
    assert order["payment_method"] == "online"
    assert order["payment_status"] == "unpaid"
    assert order["total"] == 30.0


async def test_online_payment_flow_success(client, buyer_auth, admin_auth):
    prod = await _mk_product(client, admin_auth, name="PayMe", price=30, stock=5)
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 1}, headers=buyer_auth
    )
    order = (
        await client.post(
            "/api/orders/checkout", json=_checkout(payment_method="online"), headers=buyer_auth
        )
    ).json()
    oid = order["id"]

    pay = (await client.post(f"/api/orders/{oid}/pay", headers=buyer_auth)).json()
    assert pay["gateway"] == "sandbox"
    assert pay["provider_ref"].startswith("SB-")
    assert "pay/order" in pay["payment_url"]
    assert pay["status"] == "pending"

    # initiating again returns the same pending intent
    pay2 = (await client.post(f"/api/orders/{oid}/pay", headers=buyer_auth)).json()
    assert pay2["provider_ref"] == pay["provider_ref"]

    resp = await client.post(
        f"/api/orders/{oid}/pay/simulate",
        json={"provider_ref": pay["provider_ref"], "approved": True},
        headers=buyer_auth,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "confirmed"
    assert body["payment_status"] == "paid"
    assert body["paid_at"] is not None

    # already resolved -> cannot simulate again
    resp = await client.post(
        f"/api/orders/{oid}/pay/simulate",
        json={"provider_ref": pay["provider_ref"], "approved": False},
        headers=buyer_auth,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "payment_already_resolved"


async def test_online_payment_decline_restocks(client, buyer_auth, admin_auth):
    prod = await _mk_product(client, admin_auth, name="Declined", price=10, stock=4)
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 2}, headers=buyer_auth
    )
    order = (
        await client.post(
            "/api/orders/checkout", json=_checkout(payment_method="online"), headers=buyer_auth
        )
    ).json()
    oid = order["id"]
    pay = (await client.post(f"/api/orders/{oid}/pay", headers=buyer_auth)).json()

    resp = await client.post(
        f"/api/orders/{oid}/pay/simulate",
        json={"provider_ref": pay["provider_ref"], "approved": False},
        headers=buyer_auth,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["payment_status"] == "rejected"

    # stock was restored
    updated = (await client.get(f"/api/admin/products/{prod['id']}", headers=admin_auth)).json()
    assert updated["stock"] == 4


async def test_online_payment_disabled(client, buyer_auth, admin_auth, catalog):
    resp = await client.patch(
        "/api/admin/settings", json={"online_payments_enabled": False}, headers=admin_auth
    )
    assert resp.status_code == 200, resp.text
    await client.post(
        "/api/cart/add",
        json={"product_id": catalog["product"]["id"], "quantity": 1},
        headers=buyer_auth,
    )
    resp = await client.post(
        "/api/orders/checkout", json=_checkout(payment_method="online"), headers=buyer_auth
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "payment_disabled"


async def test_pay_endpoint_ownership(client, buyer_auth, admin_auth, catalog):
    other_auth = await _other_buyer_auth()

    await client.post(
        "/api/cart/add",
        json={"product_id": catalog["product"]["id"], "quantity": 1},
        headers=buyer_auth,
    )
    order = (
        await client.post(
            "/api/orders/checkout", json=_checkout(payment_method="online"), headers=buyer_auth
        )
    ).json()

    resp = await client.post(f"/api/orders/{order['id']}/pay", headers=other_auth)
    assert resp.status_code == 404


async def test_simulate_unknown_intent(client, buyer_auth, admin_auth):
    prod = await _mk_product(client, admin_auth, name="Ghost", price=10, stock=3)
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 1}, headers=buyer_auth
    )
    order = (
        await client.post(
            "/api/orders/checkout", json=_checkout(payment_method="online"), headers=buyer_auth
        )
    ).json()
    resp = await client.post(
        f"/api/orders/{order['id']}/pay/simulate",
        json={"provider_ref": "SB-NOPE123456789", "approved": True},
        headers=buyer_auth,
    )
    assert resp.status_code == 404


async def test_simulate_disabled_outside_dev(client, buyer_auth, admin_auth, monkeypatch):
    """The sandbox self-approval endpoint must not exist outside dev/test —
    including a deployed APP_ENV=development image with DEBUG off."""
    for env in ("production", "development"):
        monkeypatch.setattr(settings, "APP_ENV", env)
        monkeypatch.setattr(settings, "DEBUG", False)
        prod = await _mk_product(client, admin_auth, name=f"NoSim{env}", price=10, stock=3)
        await client.post(
            "/api/cart/add", json={"product_id": prod["id"], "quantity": 1}, headers=buyer_auth
        )
        order = (
            await client.post(
                "/api/orders/checkout", json=_checkout(payment_method="online"), headers=buyer_auth
            )
        ).json()
        pay = (await client.post(f"/api/orders/{order['id']}/pay", headers=buyer_auth)).json()
        resp = await client.post(
            f"/api/orders/{order['id']}/pay/simulate",
            json={"provider_ref": pay["provider_ref"], "approved": True},
            headers=buyer_auth,
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "simulation_disabled"


# --- Order tracking ---------------------------------------------------------


async def test_admin_set_tracking(client, buyer_auth, admin_auth, catalog):
    await client.post(
        "/api/cart/add",
        json={"product_id": catalog["product"]["id"], "quantity": 1},
        headers=buyer_auth,
    )
    order = (await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)).json()
    oid = order["id"]

    resp = await client.patch(
        f"/api/admin/orders/{oid}/tracking",
        json={"tracking_number": "ABC123", "tracking_carrier": "GrabExpress"},
        headers=admin_auth,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tracking_number"] == "ABC123"
    assert body["tracking_carrier"] == "GrabExpress"

    # buyer sees it
    buyer_view = (await client.get(f"/api/orders/{oid}", headers=buyer_auth)).json()
    assert buyer_view["tracking_number"] == "ABC123"
    assert buyer_view["tracking_carrier"] == "GrabExpress"

    # clearing works
    resp = await client.patch(
        f"/api/admin/orders/{oid}/tracking",
        json={"tracking_number": None, "tracking_carrier": None},
        headers=admin_auth,
    )
    assert resp.status_code == 200
    assert resp.json()["tracking_number"] is None


async def test_tracking_admin_only(client, buyer_auth, catalog):
    await client.post(
        "/api/cart/add",
        json={"product_id": catalog["product"]["id"], "quantity": 1},
        headers=buyer_auth,
    )
    order = (await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)).json()
    resp = await client.patch(
        f"/api/admin/orders/{order['id']}/tracking",
        json={"tracking_number": "X"},
        headers=buyer_auth,
    )
    assert resp.status_code == 403


# --- CSV exports ------------------------------------------------------------


async def test_orders_export_csv(client, buyer_auth, admin_auth, catalog):
    await client.post(
        "/api/cart/add",
        json={"product_id": catalog["product"]["id"], "quantity": 1},
        headers=buyer_auth,
    )
    order = (await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)).json()

    resp = await client.get("/api/admin/orders/export", headers=admin_auth)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.text
    assert "order_number" in text
    assert order["order_number"] in text
    assert "123 Street, Phnom Penh" in text


async def test_customers_export_csv(client, buyer_auth, admin_auth, catalog):
    resp = await client.get("/api/admin/customers/export", headers=admin_auth)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.text
    assert "telegram_id" in text
    assert "demo_buyer" in text


async def test_exports_admin_only(client, buyer_auth):
    for path in ("/api/admin/orders/export", "/api/admin/customers/export"):
        resp = await client.get(path, headers=buyer_auth)
        assert resp.status_code == 403


# --- Saved addresses --------------------------------------------------------


async def test_addresses_crud_and_default(client, buyer_auth):
    resp = await client.post(
        "/api/addresses",
        json={
            "label": "Home",
            "recipient_name": "A",
            "recipient_phone": "+8551",
            "address": "123 Main Street",
            "is_default": True,
        },
        headers=buyer_auth,
    )
    assert resp.status_code == 200, resp.text
    home = resp.json()
    assert home["is_default"] is True

    resp = await client.post(
        "/api/addresses",
        json={
            "label": "Work",
            "recipient_name": "B",
            "recipient_phone": "+8552",
            "address": "456 Work Avenue",
            "is_default": False,
        },
        headers=buyer_auth,
    )
    assert resp.status_code == 200
    work = resp.json()
    assert work["is_default"] is False

    # first address auto-default when none set
    resp = await client.get("/api/addresses", headers=buyer_auth)
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["is_default"] is True  # default first

    # promote work -> home demoted
    resp = await client.patch(
        f"/api/addresses/{work['id']}", json={"is_default": True}, headers=buyer_auth
    )
    assert resp.status_code == 200
    items = (await client.get("/api/addresses", headers=buyer_auth)).json()["items"]
    by_label = {i["label"]: i for i in items}
    assert by_label["Home"]["is_default"] is False
    assert by_label["Work"]["is_default"] is True

    # update fields
    resp = await client.patch(
        f"/api/addresses/{home['id']}",
        json={"recipient_name": "Updated", "address": "999 New Road"},
        headers=buyer_auth,
    )
    assert resp.json()["recipient_name"] == "Updated"

    # delete default -> other promoted
    resp = await client.delete(f"/api/addresses/{work['id']}", headers=buyer_auth)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["is_default"] is True
    assert items[0]["label"] == "Home"


async def test_addresses_ownership(client, buyer_auth):
    resp = await client.post(
        "/api/addresses",
        json={"recipient_name": "Owner", "recipient_phone": "+8551", "address": "1 Owned Street"},
        headers=buyer_auth,
    )
    addr = resp.json()

    other_auth = await _other_buyer_auth()
    for method, path in (
        ("patch", f"/api/addresses/{addr['id']}"),
        ("delete", f"/api/addresses/{addr['id']}"),
    ):
        if method == "patch":
            r = await client.patch(path, json={"recipient_name": "X"}, headers=other_auth)
        else:
            r = await client.delete(path, headers=other_auth)
        assert r.status_code == 404


# --- Recently viewed --------------------------------------------------------


async def test_recently_viewed_records_only_auth(client, buyer_auth, admin_auth):
    prod = await _mk_product(client, admin_auth, name="Viewed", price=10, stock=5)

    # anonymous view -> not recorded
    await client.get(f"/api/products/{prod['id']}")

    # authenticated view -> recorded
    await client.get(f"/api/products/{prod['id']}", headers=buyer_auth)

    resp = await client.get("/api/me/recently-viewed", headers=buyer_auth)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [p["id"] for p in items] == [prod["id"]]


async def test_recently_viewed_requires_auth(client):
    resp = await client.get("/api/me/recently-viewed")
    assert resp.status_code == 403


# --- Broadcasts -------------------------------------------------------------


async def test_broadcast_to_buyers(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text, bot_token=None):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr("app.api.admin.broadcasts.send_telegram_message", _send)

    # A buyer becomes a customer by ordering from this store.
    prod = await _mk_product(client, admin_auth, name="BroadcastMe", price=10, stock=5)
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 1}, headers=buyer_auth
    )
    await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)

    resp = await client.post(
        "/api/admin/broadcasts", json={"message": "Hello everyone!"}, headers=admin_auth
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1  # only the buyer, not the admin
    assert body["sent"] == 1
    assert len(sent) == 1
    assert "Hello everyone!" in sent[0][1]


async def test_broadcast_scoped_to_store_customers(
    client, buyer_auth, admin_auth, monkeypatch
):
    """A buyer who never ordered from this store must not receive its broadcast."""
    sent = []

    async def _send(chat_id, text, bot_token=None):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr("app.api.admin.broadcasts.send_telegram_message", _send)

    other_auth = await _other_buyer_auth()  # exists as a buyer, but never orders

    resp = await client.post(
        "/api/admin/broadcasts", json={"message": "Only customers!"}, headers=admin_auth
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 0
    assert body["sent"] == 0
    assert len(sent) == 0
    assert other_auth  # other buyer still exists in the DB


async def test_broadcast_admin_only(client, buyer_auth):
    resp = await client.post(
        "/api/admin/broadcasts", json={"message": "nope"}, headers=buyer_auth
    )
    assert resp.status_code == 403


# --- Admin low-stock alerts -------------------------------------------------


async def test_low_stock_admin_alert_on_order(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text, bot_token=None):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr("app.core.telegram.send_telegram_message", _send)

    prod = await _mk_product(client, admin_auth, name="Rare", price=10, stock=6)
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 2}, headers=buyer_auth
    )
    await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)

    assert len(sent) == 1
    assert "Low stock" in sent[0][1]
    assert "Rare" in sent[0][1]


async def test_back_in_stock_admin_alert(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text, bot_token=None):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr("app.core.telegram.send_telegram_message", _send)

    prod = await _mk_product(client, admin_auth, name="Restock", price=10, stock=0)
    assert sent == []

    resp = await client.patch(f"/api/admin/products/{prod['id']}", json={"stock": 8}, headers=admin_auth)
    assert resp.status_code == 200, resp.text
    assert len(sent) == 1
    assert "Back in stock" in sent[0][1]


async def test_low_stock_alert_on_product_create(client, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text, bot_token=None):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr("app.core.telegram.send_telegram_message", _send)

    resp = await client.post(
        "/api/admin/products",
        json={"name": "Slim", "price": 5, "stock": 2},
        headers=admin_auth,
    )
    assert resp.status_code == 200, resp.text
    assert len(sent) == 1
    assert "Low stock" in sent[0][1]
    assert "Slim" in sent[0][1]


async def test_no_alert_without_transition(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text, bot_token=None):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr("app.core.telegram.send_telegram_message", _send)

    prod = await _mk_product(client, admin_auth, name="Steady", price=10, stock=9)
    # edit that keeps stock above threshold -> no alert
    await client.patch(f"/api/admin/products/{prod['id']}", json={"stock": 8}, headers=admin_auth)
    assert sent == []

    # still-low edit -> no repeat alert
    await client.patch(f"/api/admin/products/{prod['id']}", json={"stock": 4}, headers=admin_auth)
    assert len(sent) == 1  # only the crossing above->below


async def test_low_stock_alert_uses_settings_threshold(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text, bot_token=None):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr("app.core.telegram.send_telegram_message", _send)

    await client.patch("/api/admin/settings", json={"low_stock_threshold": 10}, headers=admin_auth)

    prod = await _mk_product(client, admin_auth, name="Broad", price=10, stock=12)
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 3}, headers=buyer_auth
    )
    await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)

    assert len(sent) == 1
    assert "Low stock" in sent[0][1]
