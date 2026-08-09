async def test_export_products_csv(client, admin_auth, catalog):
    resp = await client.get("/api/admin/products/export", headers=admin_auth)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Test Product" in resp.text
    assert "name,price" in resp.text


async def test_export_products_blocks_formula_injection(client, admin_auth):
    await client.post(
        "/api/admin/products",
        json={"name": "=SUM(A1:A100)", "price": 5, "stock": 1},
        headers=admin_auth,
    )
    resp = await client.get("/api/admin/products/export", headers=admin_auth)
    assert resp.status_code == 200
    assert "'=SUM(A1:A100)" in resp.text
    assert "\n=SUM(A1:A100)" not in resp.text


async def test_export_orders_blocks_formula_injection(client, buyer_auth, admin_auth, catalog):
    await client.post(
        "/api/cart/add",
        json={"product_id": catalog["product"]["id"], "quantity": 1},
        headers=buyer_auth,
    )
    await client.post(
        "/api/orders/checkout",
        json={
            "payment_method": "cod",
            "recipient_name": "=cmd|' /C calc'!A0",
            "recipient_phone": "@evil.example.com",
            "delivery_address": "+1+1+1",
            "delivery_note": "",
        },
        headers=buyer_auth,
    )
    resp = await client.get("/api/admin/orders/export", headers=admin_auth)
    assert resp.status_code == 200
    assert "'=cmd|' /C calc'!A0" in resp.text
    assert "'@evil.example.com" in resp.text
    assert "'+1+1" in resp.text


async def test_export_requires_admin(client, buyer_auth):
    resp = await client.get("/api/admin/products/export", headers=buyer_auth)
    assert resp.status_code == 403


async def test_import_products_csv(client, admin_auth):
    csv_content = (
        "name,price,category,sku,stock,is_featured,status,description\n"
        "Imported Widget,25.5,Gadgets,SKU-1,10,1,active,From CSV\n"
    )
    resp = await client.post(
        "/api/admin/products/import",
        files={"file": ("products.csv", csv_content, "text/csv")},
        headers=admin_auth,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] == 1

    cats = await client.get("/api/categories")
    assert any(c["name"] == "Gadgets" for c in cats.json())

    prods = (await client.get("/api/admin/products?search=Imported", headers=admin_auth)).json()
    assert prods["items"][0]["price"] == 25.5
    assert prods["items"][0]["stock"] == 10


async def test_import_upserts_by_sku(client, admin_auth):
    csv1 = "name,price,sku\nWidget A,10,SKU-X\n"
    resp = await client.post(
        "/api/admin/products/import", files={"file": ("p.csv", csv1, "text/csv")}, headers=admin_auth
    )
    assert resp.json()["created"] == 1

    csv2 = "name,price,sku\nWidget A Renamed,20,SKU-X\n"
    resp = await client.post(
        "/api/admin/products/import", files={"file": ("p.csv", csv2, "text/csv")}, headers=admin_auth
    )
    body = resp.json()
    assert body["updated"] == 1

    prods = (await client.get("/api/admin/products?search=Widget", headers=admin_auth)).json()
    assert prods["total"] == 1
    assert prods["items"][0]["price"] == 20
    assert prods["items"][0]["name"] == "Widget A Renamed"


async def test_import_requires_csv(client, admin_auth):
    resp = await client.post(
        "/api/admin/products/import",
        files={"file": ("data.txt", "hello", "text/plain")},
        headers=admin_auth,
    )
    assert resp.status_code == 409
