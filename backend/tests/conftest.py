import os
import tempfile

import httpx
import pytest
import pytest_asyncio

_tmp = tempfile.mkdtemp()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_tmp}/test.db")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456789:TEST-BOT-TOKEN")
os.environ.setdefault("ADMIN_TELEGRAM_IDS", "1")
os.environ.setdefault("UPLOAD_DIR", _tmp)
os.environ.setdefault("TELEGRAM_AUTH_MAX_AGE_SECONDS", "86400")

from app.api.deps import get_db  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import AsyncSessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_db(prepare_db):
    from app.api.deps import reset_rate_limits

    reset_rate_limits()
    async with AsyncSessionLocal() as db:
        for table in reversed(Base.metadata.sorted_tables):
            await db.execute(table.delete())
        await db.commit()
    yield


@pytest.fixture(autouse=True)
def _mock_telegram_send(monkeypatch):
    """Never hit the real Telegram API from tests."""

    async def _noop(*args, **kwargs):
        return False

    monkeypatch.setattr("app.services.notifications.send_telegram_message", _noop)
    monkeypatch.setattr("app.core.telegram.send_telegram_message", _noop)


async def _get_db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(prepare_db):
    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def login(client, role: str = "buyer") -> dict:
    resp = await client.post(f"/api/auth/demo?role={role}")
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def buyer_auth(client):
    token = await login(client, "buyer")
    return auth(token)


@pytest_asyncio.fixture
async def admin_auth(client):
    token = await login(client, "admin")
    return auth(token)


@pytest_asyncio.fixture
async def catalog(client, admin_auth):
    """Create a category and an active product, return their ids."""
    cat = await client.post(
        "/api/admin/categories",
        json={"name": "Test Category", "slug": "test-category"},
        headers=admin_auth,
    )
    assert cat.status_code == 200, cat.text
    prod = await client.post(
        "/api/admin/products",
        json={
            "name": "Test Product",
            "price": 100,
            "stock": 10,
            "category_id": cat.json()["id"],
        },
        headers=admin_auth,
    )
    assert prod.status_code == 200, prod.text
    return {"category": cat.json(), "product": prod.json()}
