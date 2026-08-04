import datetime as dt

from sqlalchemy import select, update

from app.db.session import AsyncSessionLocal
from app.models import CartItem, StockAlert
from app.services.reminders import send_abandoned_cart_reminders


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


async def _complete_order(client, admin_auth, oid):
    for status in ("confirmed", "processing", "shipped", "delivered", "completed"):
        resp = await client.patch(
            f"/api/admin/orders/{oid}/status", json={"status": status}, headers=admin_auth
        )
        assert resp.status_code == 200, resp.text


# --- Product variants -------------------------------------------------------


async def test_admin_create_product_with_variants(client, admin_auth):
    prod = await _mk_product(
        client,
        admin_auth,
        name="T-Shirt",
        variants=[
            {"name": "Red / M", "options": {"color": "red", "size": "M"}, "price": 22, "stock": 5},
            {"name": "Blue / L", "options": {"color": "blue", "size": "L"}, "price": 24, "stock": 0},
        ],
    )
    assert len(prod["variants"]) == 2
    red = prod["variants"][0]
    assert red["name"] == "Red / M"
    assert red["price"] == 22.0
    assert red["in_stock"] is True
    assert red["is_active"] is True
    blue = prod["variants"][1]
    assert blue["in_stock"] is False


async def test_admin_update_variants_delete_removed(client, admin_auth):
    prod = await _mk_product(
        client, admin_auth, name="Shoes", variants=[{"name": "42", "price": 30, "stock": 3}]
    )
    vid = prod["variants"][0]["id"]
    resp = await client.patch(
        f"/api/admin/products/{prod['id']}",
        json={
            "variants": [
                {"id": vid, "name": "43", "price": 32, "stock": 4},
                {"name": "44", "price": 32, "stock": 2},
            ]
        },
        headers=admin_auth,
    )
    assert resp.status_code == 200, resp.text
    variants = resp.json()["variants"]
    assert [v["name"] for v in variants] == ["43", "44"]
    assert all(v["id"] is not None for v in variants)


async def test_buyer_sees_active_variants(client, admin_auth):
    prod = await _mk_product(
        client,
        admin_auth,
        name="Hat",
        variants=[
            {"name": "Small", "stock": 4},
            {"name": "Large", "stock": 0, "is_active": False},
        ],
    )
    resp = await client.get(f"/api/products/{prod['id']}")
    assert resp.status_code == 200
    variants = resp.json()["variants"]
    assert [v["name"] for v in variants] == ["Small"]
    assert variants[0]["in_stock"] is True


async def test_cart_checkout_with_variant_decrements_variant_stock(
    client, buyer_auth, admin_auth
):
    prod = await _mk_product(
        client, admin_auth, name="Backpack", price=10, stock=5,
        variants=[{"name": "Green", "price": 12, "stock": 4}],
    )
    vid = prod["variants"][0]["id"]
    resp = await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "variant_id": vid, "quantity": 2},
        headers=buyer_auth,
    )
    assert resp.status_code == 200, resp.text
    cart = resp.json()
    assert cart["item_count"] == 2
    assert cart["subtotal"] == 24.0
    assert cart["items"][0]["variant"]["name"] == "Green"
    assert cart["items"][0]["unit_price"] == 12.0

    order = (
        await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)
    ).json()
    assert order["items"][0]["variant_name"] == "Green"
    assert order["items"][0]["unit_price"] == 12.0

    updated = (await client.get(f"/api/admin/products/{prod['id']}", headers=admin_auth)).json()
    assert updated["variants"][0]["stock"] == 2


async def test_cart_variant_overstock_rejected(client, buyer_auth, admin_auth):
    prod = await _mk_product(
        client, admin_auth, name="Cup", variants=[{"name": "Red", "stock": 2}]
    )
    vid = prod["variants"][0]["id"]
    resp = await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "variant_id": vid, "quantity": 5},
        headers=buyer_auth,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "insufficient_stock"


# --- Quantity-discount price tiers ------------------------------------------


async def test_quantity_tier_pricing(client, buyer_auth, admin_auth):
    prod = await _mk_product(
        client, admin_auth, name="Tea", price=20, price_tiers=[{"min_quantity": 3, "price": 18}]
    )
    r = await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 2}, headers=buyer_auth
    )
    assert r.json()["subtotal"] == 40.0

    r = await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 3}, headers=buyer_auth
    )
    assert r.json()["item_count"] == 5
    assert r.json()["items"][0]["unit_price"] == 18.0
    assert r.json()["subtotal"] == 90.0


async def test_tier_pricing_ignores_non_tier_quantities(client, buyer_auth, admin_auth):
    prod = await _mk_product(
        client, admin_auth, name="Gadget", price=10,
        price_tiers=[{"min_quantity": 10, "price": 8}],
    )
    r = await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 9}, headers=buyer_auth
    )
    assert r.json()["subtotal"] == 90.0


# --- Buyer search & sort ----------------------------------------------------


async def test_search_matches_description_and_sku(client, admin_auth):
    await _mk_product(
        client, admin_auth, name="Laptop", price=100, sku="LT-1",
        description="powerful gaming machine",
    )
    await _mk_product(client, admin_auth, name="Mouse", price=20, sku="MS-1", description="ergonomic")

    r = await client.get("/api/products", params={"search": "gaming"})
    assert r.status_code == 200
    names = [p["name"] for p in r.json()["items"]]
    assert names == ["Laptop"]

    r = await client.get("/api/products", params={"search": "MS-1"})
    assert [p["name"] for p in r.json()["items"]] == ["Mouse"]


async def test_sort_price_and_popular(client, buyer_auth, admin_auth):
    cheap = await _mk_product(client, admin_auth, name="Cheap", price=5, stock=50)
    pricey = await _mk_product(client, admin_auth, name="Pricey", price=50, stock=50)
    medium = await _mk_product(client, admin_auth, name="Medium", price=25, stock=50)

    r = await client.get("/api/products", params={"sort": "price_asc"})
    assert [p["name"] for p in r.json()["items"]][:3] == ["Cheap", "Medium", "Pricey"]

    r = await client.get("/api/products", params={"sort": "price_desc"})
    assert [p["name"] for p in r.json()["items"]][:3] == ["Pricey", "Medium", "Cheap"]

    # popular = most sold first
    await client.post(
        "/api/cart/add", json={"product_id": pricey["id"], "quantity": 3}, headers=buyer_auth
    )
    await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)
    r = await client.get("/api/products", params={"sort": "popular"})
    assert [p["name"] for p in r.json()["items"]][0] == "Pricey"


# --- Back-in-stock alerts ---------------------------------------------------


async def test_stock_alert_product_restock(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text):
        sent.append(text)
        return True

    monkeypatch.setattr("app.services.stock_alerts.send_telegram_message", _send)

    prod = await _mk_product(client, admin_auth, name="Sneaker", price=50, stock=0)
    pid = prod["id"]

    resp = await client.post(f"/api/products/{pid}/stock-alert", json={}, headers=buyer_auth)
    assert resp.status_code == 200, resp.text
    # idempotent
    resp = await client.post(f"/api/products/{pid}/stock-alert", json={}, headers=buyer_auth)
    assert resp.status_code == 200

    resp = await client.patch(f"/api/admin/products/{pid}", json={"stock": 5}, headers=admin_auth)
    assert resp.status_code == 200, resp.text
    assert len(sent) == 1
    assert "Sneaker" in sent[0]

    async with AsyncSessionLocal() as db:
        alerts = (await db.execute(select(StockAlert))).scalars().all()
        assert all(a.is_notified for a in alerts)


async def test_stock_alert_in_stock_rejected(client, buyer_auth, admin_auth):
    prod = await _mk_product(client, admin_auth, name="Pillow", price=10, stock=4)
    resp = await client.post(f"/api/products/{prod['id']}/stock-alert", json={}, headers=buyer_auth)
    assert resp.status_code == 400
    assert resp.json()["code"] == "in_stock_already"


async def test_variant_stock_alert_and_unsubscribe(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text):
        sent.append(text)
        return True

    monkeypatch.setattr("app.services.stock_alerts.send_telegram_message", _send)

    prod = await _mk_product(
        client, admin_auth, name="Shirt", price=10, stock=5,
        variants=[{"name": "Green", "stock": 0}],
    )
    pid = prod["id"]
    vid = prod["variants"][0]["id"]

    resp = await client.post(
        f"/api/products/{pid}/stock-alert", json={"variant_id": vid}, headers=buyer_auth
    )
    assert resp.status_code == 200

    await client.patch(
        f"/api/admin/products/{pid}",
        json={"variants": [{"id": vid, "name": "Green", "stock": 3}]},
        headers=admin_auth,
    )
    assert len(sent) == 1
    assert "Green" in sent[0]

    # unsubscribe, restock again -> no new notification
    resp = await client.delete(f"/api/products/{pid}/stock-alert", headers=buyer_auth)
    assert resp.status_code == 200
    await client.patch(
        f"/api/admin/products/{pid}",
        json={"variants": [{"id": vid, "name": "Green", "stock": 4}]},
        headers=admin_auth,
    )
    assert len(sent) == 1


async def test_csv_import_triggers_restock_alerts(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text):
        sent.append(text)
        return True

    monkeypatch.setattr("app.services.stock_alerts.send_telegram_message", _send)

    prod = await _mk_product(client, admin_auth, name="Candle", price=5, stock=0)
    pid = prod["id"]
    await client.post(f"/api/products/{pid}/stock-alert", json={}, headers=buyer_auth)

    csv_data = "name,price,stock,sku\nCandle,5,7,CND-1\n"
    resp = await client.post(
        "/api/admin/products/import",
        files={"file": ("products.csv", csv_data.encode(), "text/csv")},
        headers=admin_auth,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["updated"] == 1
    assert len(sent) == 1


# --- Abandoned-cart reminders -----------------------------------------------


async def test_abandoned_cart_reminder_sent_once(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr("app.services.reminders.send_telegram_message", _send)

    prod = await _mk_product(client, admin_auth, name="Candle", price=5)
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 2}, headers=buyer_auth
    )

    stale = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)
    async with AsyncSessionLocal() as db:
        await db.execute(update(CartItem).values(updated_at=stale))
        await db.commit()

    async with AsyncSessionLocal() as db:
        sent_count = await send_abandoned_cart_reminders(db, hours=24)
        await db.commit()
    assert sent_count == 1
    assert len(sent) == 1
    assert "Candle" in sent[0][1]

    # already nudged -> not sent again
    async with AsyncSessionLocal() as db:
        sent_count = await send_abandoned_cart_reminders(db, hours=24)
        await db.commit()
    assert sent_count == 0
    assert len(sent) == 1


async def test_reminder_skips_fresh_cart(client, buyer_auth, admin_auth, monkeypatch):
    sent = []

    async def _send(chat_id, text):
        sent.append(text)
        return True

    monkeypatch.setattr("app.services.reminders.send_telegram_message", _send)

    prod = await _mk_product(client, admin_auth, name="Fresh", price=5)
    await client.post(
        "/api/cart/add", json={"product_id": prod["id"], "quantity": 1}, headers=buyer_auth
    )
    async with AsyncSessionLocal() as db:
        sent_count = await send_abandoned_cart_reminders(db, hours=24)
        await db.commit()
    assert sent_count == 0
    assert sent == []


# --- Reorder ----------------------------------------------------------------


async def test_reorder_skips_unavailable(client, buyer_auth, admin_auth):
    a = await _mk_product(client, admin_auth, name="Book", price=15, stock=10)
    b = await _mk_product(client, admin_auth, name="Pen", price=2, stock=3)

    await client.post(
        "/api/cart/add", json={"product_id": a["id"], "quantity": 2}, headers=buyer_auth
    )
    await client.post(
        "/api/cart/add", json={"product_id": b["id"], "quantity": 1}, headers=buyer_auth
    )
    order = (await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)).json()

    # Pen goes out of stock
    await client.patch(f"/api/admin/products/{b['id']}", json={"stock": 0}, headers=admin_auth)

    await client.delete("/api/cart", headers=buyer_auth)
    resp = await client.post(f"/api/orders/{order['id']}/reorder", headers=buyer_auth)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["added"] == 1
    assert body["skipped"] == 1
    assert body["cart"]["item_count"] == 2
    assert body["cart"]["items"][0]["product"]["name"] == "Book"


async def test_reorder_with_variant(client, buyer_auth, admin_auth):
    prod = await _mk_product(
        client, admin_auth, name="Socks", price=5, stock=10,
        variants=[{"name": "White", "price": 6, "stock": 5}],
    )
    vid = prod["variants"][0]["id"]
    await client.post(
        "/api/cart/add",
        json={"product_id": prod["id"], "variant_id": vid, "quantity": 2},
        headers=buyer_auth,
    )
    order = (await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)).json()
    await client.delete("/api/cart", headers=buyer_auth)

    resp = await client.post(f"/api/orders/{order['id']}/reorder", headers=buyer_auth)
    assert resp.status_code == 200
    item = resp.json()["cart"]["items"][0]
    assert item["variant"]["name"] == "White"
    assert item["unit_price"] == 6.0


# --- Admin customer management ----------------------------------------------


async def test_admin_customers_list_detail_update(client, buyer_auth, admin_auth, catalog):
    await client.post(
        "/api/cart/add", json={"product_id": catalog["product"]["id"], "quantity": 1},
        headers=buyer_auth,
    )
    order = (await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)).json()
    await _complete_order(client, admin_auth, order["id"])

    resp = await client.get("/api/admin/customers", headers=admin_auth)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert all(c["role"] != "admin" for c in body["items"])
    cust = body["items"][0]
    assert cust["orders_count"] == 1
    assert cust["total_spent"] == 100.0
    assert cust["last_order_at"] is not None
    cid = cust["id"]

    resp = await client.get("/api/admin/customers", params={"search": "demo_buyer"}, headers=admin_auth)
    assert resp.json()["total"] == 1
    resp = await client.get("/api/admin/customers", params={"search": "zzz-no-match"}, headers=admin_auth)
    assert resp.json()["total"] == 0

    resp = await client.get(f"/api/admin/customers/{cid}", headers=admin_auth)
    assert resp.status_code == 200
    assert resp.json()["orders"][0]["order_number"] == order["order_number"]

    resp = await client.patch(
        f"/api/admin/customers/{cid}", json={"is_active": False, "note": "VIP"}, headers=admin_auth
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert resp.json()["note"] == "VIP"


async def test_admin_customer_pending_order_not_paid(client, buyer_auth, admin_auth, catalog):
    await client.post(
        "/api/cart/add", json={"product_id": catalog["product"]["id"], "quantity": 1},
        headers=buyer_auth,
    )
    await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)

    resp = await client.get("/api/admin/customers", headers=admin_auth)
    cust = resp.json()["items"][0]
    assert cust["orders_count"] == 1
    assert cust["total_spent"] == 0.0


# --- Order refunds ----------------------------------------------------------


async def test_admin_refund_order(client, buyer_auth, admin_auth, catalog):
    await client.post(
        "/api/cart/add", json={"product_id": catalog["product"]["id"], "quantity": 1},
        headers=buyer_auth,
    )
    order = (await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)).json()
    oid = order["id"]
    await client.patch(f"/api/admin/orders/{oid}/status", json={"status": "confirmed"}, headers=admin_auth)

    # amount exceeding total rejected
    resp = await client.post(
        f"/api/admin/orders/{oid}/refund", json={"amount": 999, "reason": "x"}, headers=admin_auth
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_refund_amount"

    resp = await client.post(
        f"/api/admin/orders/{oid}/refund", json={"amount": 50, "reason": "partial"}, headers=admin_auth
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "refunded"
    assert body["payment_status"] == "refunded"
    assert body["refund_amount"] == 50.0
    assert body["refund_reason"] == "partial"
    assert body["refunded_at"] is not None

    # buyer sees refund fields
    buyer_view = (await client.get(f"/api/orders/{oid}", headers=buyer_auth)).json()
    assert buyer_view["status"] == "refunded"
    assert buyer_view["refund_amount"] == 50.0

    # terminal order cannot be refunded again
    resp = await client.post(
        f"/api/admin/orders/{oid}/refund", json={"amount": 10}, headers=admin_auth
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "order_terminal"


# --- Dashboard analytics ----------------------------------------------------


async def test_dashboard_analytics(client, buyer_auth, admin_auth, catalog):
    resp = await client.post(
        "/api/admin/coupons",
        json={"code": "SAVE10", "discount_type": "percent", "value": 10, "per_user_limit": 5},
        headers=admin_auth,
    )
    assert resp.status_code == 200, resp.text

    # order 1 with coupon: subtotal 200, discount 20, total 180
    await client.post(
        "/api/cart/add", json={"product_id": catalog["product"]["id"], "quantity": 2},
        headers=buyer_auth,
    )
    order1 = (await client.post("/api/orders/checkout", json=_checkout(coupon_code="SAVE10"), headers=buyer_auth)).json()
    await _complete_order(client, admin_auth, order1["id"])

    # order 2 plain: total 200
    await client.post(
        "/api/cart/add", json={"product_id": catalog["product"]["id"], "quantity": 2},
        headers=buyer_auth,
    )
    order2 = (await client.post("/api/orders/checkout", json=_checkout(), headers=buyer_auth)).json()
    await _complete_order(client, admin_auth, order2["id"])

    resp = await client.get("/api/admin/dashboard", headers=admin_auth)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert float(body["total_revenue"]) == 380.0
    assert body["total_orders"] == 2
    assert float(body["avg_order_value"]) == 190.0
    assert body["repeat_customer_rate"] == 100.0
    assert float(body["total_discount_given"]) == 20.0
    assert body["coupon_redemptions"] == [{"code": "SAVE10", "redemptions": 1}]
    assert body["revenue_by_category"][0]["name"] == "Test Category"
    assert body["revenue_by_category"][0]["revenue"] == 400.0
