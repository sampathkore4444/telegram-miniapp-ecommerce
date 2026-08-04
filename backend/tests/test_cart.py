async def test_add_to_cart(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    resp = await client.post("/api/cart/add", json={"product_id": pid, "quantity": 2}, headers=buyer_auth)
    assert resp.status_code == 200
    cart = resp.json()
    assert cart["item_count"] == 2
    assert cart["subtotal"] == 200.0


async def test_add_twice_increments(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    for _ in range(2):
        await client.post("/api/cart/add", json={"product_id": pid, "quantity": 1}, headers=buyer_auth)
    cart = await client.get("/api/cart", headers=buyer_auth)
    assert cart.json()["item_count"] == 2


async def test_cart_overstock_rejected(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    resp = await client.post("/api/cart/add", json={"product_id": pid, "quantity": 99}, headers=buyer_auth)
    assert resp.status_code == 400
    assert resp.json()["code"] == "insufficient_stock"


async def test_update_quantity(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    await client.post("/api/cart/add", json={"product_id": pid, "quantity": 1}, headers=buyer_auth)
    cart = await client.get("/api/cart", headers=buyer_auth)
    item_id = cart.json()["items"][0]["id"]

    resp = await client.patch(f"/api/cart/{item_id}", json={"quantity": 5}, headers=buyer_auth)
    assert resp.status_code == 200
    assert resp.json()["item_count"] == 5

    resp = await client.patch(f"/api/cart/{item_id}", json={"quantity": 0}, headers=buyer_auth)
    assert resp.json()["item_count"] == 0


async def test_clear_cart(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    await client.post("/api/cart/add", json={"product_id": pid, "quantity": 1}, headers=buyer_auth)
    resp = await client.delete("/api/cart", headers=buyer_auth)
    assert resp.json()["item_count"] == 0
