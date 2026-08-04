async def test_wishlist_add_list_remove(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    resp = await client.post("/api/wishlist", json={"product_id": pid}, headers=buyer_auth)
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/wishlist", headers=buyer_auth)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["product"]["id"] == pid

    resp = await client.delete(f"/api/wishlist/{pid}", headers=buyer_auth)
    assert resp.status_code == 200
    data = (await client.get("/api/wishlist", headers=buyer_auth)).json()
    assert data["count"] == 0


async def test_wishlist_duplicate_is_idempotent(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    await client.post("/api/wishlist", json={"product_id": pid}, headers=buyer_auth)
    await client.post("/api/wishlist", json={"product_id": pid}, headers=buyer_auth)
    data = (await client.get("/api/wishlist", headers=buyer_auth)).json()
    assert data["count"] == 1


async def test_wishlist_missing_product(client, buyer_auth):
    resp = await client.post("/api/wishlist", json={"product_id": 9999}, headers=buyer_auth)
    assert resp.status_code == 404


async def test_wishlist_requires_auth(client, catalog):
    resp = await client.get("/api/wishlist")
    assert resp.status_code == 403
