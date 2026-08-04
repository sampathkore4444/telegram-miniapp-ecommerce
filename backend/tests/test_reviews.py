async def test_submit_and_list_review(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    resp = await client.post(
        f"/api/products/{pid}/reviews", json={"rating": 5, "comment": "Great!"}, headers=buyer_auth
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/products/{pid}/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["count"] == 1
    assert data["summary"]["average"] == 5.0
    assert data["items"][0]["rating"] == 5
    assert data["items"][0]["user_name"]


async def test_review_average_and_distribution(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    from app.core.security import create_access_token
    from app.db.session import AsyncSessionLocal
    from app.models import User
    from sqlalchemy import select

    async def _other_auth(tg_id, username):
        async with AsyncSessionLocal() as db:
            db.add(User(telegram_id=tg_id, username=username, first_name="Second"))
            await db.commit()
            other_id = (await db.execute(select(User).where(User.telegram_id == tg_id))).scalar_one().id
        return {"Authorization": f"Bearer {create_access_token(other_id, 'buyer')}"}

    await client.post(f"/api/products/{pid}/reviews", json={"rating": 5}, headers=buyer_auth)
    rev2 = await _other_auth(777001, "rev2")
    await client.post(f"/api/products/{pid}/reviews", json={"rating": 3}, headers=rev2)
    rev3 = await _other_auth(777002, "rev3")
    await client.post(f"/api/products/{pid}/reviews", json={"rating": 4}, headers=rev3)

    data = (await client.get(f"/api/products/{pid}/reviews")).json()
    assert data["summary"]["count"] == 3
    assert data["summary"]["average"] == 4.0
    assert data["summary"]["distribution"]["5"] == 1


async def test_review_duplicate_rejected(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    await client.post(
        f"/api/products/{pid}/reviews", json={"rating": 4, "comment": "ok"}, headers=buyer_auth
    )
    resp = await client.post(
        f"/api/products/{pid}/reviews", json={"rating": 4, "comment": "again"}, headers=buyer_auth
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "already_reviewed"


async def test_review_rating_validation(client, buyer_auth, catalog):
    pid = catalog["product"]["id"]
    resp = await client.post(f"/api/products/{pid}/reviews", json={"rating": 9}, headers=buyer_auth)
    assert resp.status_code == 422


async def test_review_requires_auth(client, catalog):
    pid = catalog["product"]["id"]
    resp = await client.post(f"/api/products/{pid}/reviews", json={"rating": 5})
    assert resp.status_code == 403


async def test_admin_hides_review(client, buyer_auth, admin_auth, catalog):
    pid = catalog["product"]["id"]
    review = (
        await client.post(
            f"/api/products/{pid}/reviews", json={"rating": 3, "comment": "meh"}, headers=buyer_auth
        )
    ).json()
    rid = review["id"]

    resp = await client.patch(f"/api/admin/reviews/{rid}", json={"is_approved": False}, headers=admin_auth)
    assert resp.status_code == 200

    public = (await client.get(f"/api/products/{pid}/reviews")).json()
    assert public["summary"]["count"] == 0

    admin_list = (await client.get("/api/admin/reviews?status=hidden", headers=admin_auth)).json()
    assert admin_list["total"] == 1
