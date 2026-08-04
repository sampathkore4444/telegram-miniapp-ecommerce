from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbDep

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health(db: DbDep):
    await db.execute(text("SELECT 1"))
    return {"ok": True}
