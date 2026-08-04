async def test_admin_create_update_delete_product(client, admin_auth):
    resp = await client.post(
        "/api/admin/products",
        json={"name": "New Gadget", "price": 12.5, "stock": 5},
        headers=admin_auth,
    )
    assert resp.status_code == 200, resp.text
    product = resp.json()
    assert product["slug"] == "new-gadget"
    pid = product["id"]

    resp = await client.patch(
        f"/api/admin/products/{pid}", json={"price": 15, "stock": 8}, headers=admin_auth
    )
    assert resp.status_code == 200
    assert resp.json()["price"] == 15.0

    resp = await client.delete(f"/api/admin/products/{pid}", headers=admin_auth)
    assert resp.status_code == 204

    resp = await client.get(f"/api/admin/products/{pid}", headers=admin_auth)
    assert resp.status_code == 404


async def test_admin_duplicate_name_gets_unique_slug(client, admin_auth, catalog):
    resp = await client.post(
        "/api/admin/products",
        json={"name": "Test Product", "price": 1, "stock": 1},
        headers=admin_auth,
    )
    # Same name -> auto-unique slug rather than a conflict error.
    assert resp.status_code == 200
    assert resp.json()["slug"] != "test-product"


async def test_admin_categories_crud(client, admin_auth):
    created = await client.post(
        "/api/admin/categories", json={"name": "Sports", "slug": "sports"}, headers=admin_auth
    )
    assert created.status_code == 200
    cid = created.json()["id"]

    updated = await client.patch(
        f"/api/admin/categories/{cid}", json={"name": "Sports Gear"}, headers=admin_auth
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Sports Gear"

    deleted = await client.delete(f"/api/admin/categories/{cid}", headers=admin_auth)
    assert deleted.status_code == 204


async def test_dashboard_stats(client, admin_auth, buyer_auth, catalog):
    await client.post(
        "/api/cart/add", json={"product_id": catalog["product"]["id"], "quantity": 1}, headers=buyer_auth
    )
    order = (
        await client.post(
            "/api/orders/checkout",
            json={
                "payment_method": "cod",
                "recipient_name": "X",
                "recipient_phone": "123",
                "delivery_address": "Addr 1",
            },
            headers=buyer_auth,
        )
    ).json()
    for status in ("confirmed", "processing", "shipped", "delivered"):
        resp = await client.patch(
            f"/api/admin/orders/{order['id']}/status", json={"status": status}, headers=admin_auth
        )
        assert resp.status_code == 200, resp.text

    resp = await client.get("/api/admin/dashboard", headers=admin_auth)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_orders"] == 1
    assert float(data["total_revenue"]) == 100.0
    assert data["products_count"] == 1
    assert data["top_products"][0]["name"] == "Test Product"


async def test_settings_update(client, admin_auth):
    resp = await client.patch(
        "/api/admin/settings",
        json={"store_name": "My Shop 2", "delivery_fee": 3, "free_delivery_threshold": 50},
        headers=admin_auth,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["store_name"] == "My Shop 2"
    assert body["delivery_fee"] == 3.0
    assert body["free_delivery_threshold"] == 50.0
