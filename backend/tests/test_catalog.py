async def test_public_product_list(client, catalog):
    resp = await client.get("/api/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Test Product"


async def test_public_product_detail(client, catalog):
    pid = catalog["product"]["id"]
    resp = await client.get(f"/api/products/{pid}")
    assert resp.status_code == 200
    assert resp.json()["price"] == 100.0


async def test_public_product_detail_missing(client):
    resp = await client.get("/api/products/99999")
    assert resp.status_code == 404


async def test_categories(client, catalog):
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "Test Category" in names


async def test_product_search(client, catalog):
    resp = await client.get("/api/products", params={"search": "Test"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = await client.get("/api/products", params={"search": "nope"})
    assert resp.json()["total"] == 0


async def test_inactive_product_hidden(client, catalog, admin_auth):
    pid = catalog["product"]["id"]
    await client.patch(
        f"/api/admin/products/{pid}",
        json={"status": "archived"},
        headers=admin_auth,
    )
    resp = await client.get(f"/api/products/{pid}")
    assert resp.status_code == 404
