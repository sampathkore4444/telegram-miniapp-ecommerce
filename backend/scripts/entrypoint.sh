#!/bin/sh
set -e

echo "[entrypoint] waiting for database..."
python - <<'PY'
import asyncio
from sqlalchemy import text
from app.core.config import get_settings
from app.db.session import engine

async def wait():
    for i in range(60):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("[entrypoint] database is ready")
            return
        except Exception as exc:  # noqa: BLE001
            if i % 5 == 0:
                print(f"[entrypoint] db not ready ({exc}); retrying...")
            await asyncio.sleep(1)
    raise SystemExit("database did not become ready")

asyncio.run(wait())
PY

echo "[entrypoint] running migrations..."
alembic upgrade head

echo "[entrypoint] seeding..."
python -m app.scripts.seed

exec "$@"
