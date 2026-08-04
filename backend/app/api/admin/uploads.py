from fastapi import APIRouter, UploadFile

from app.api.deps import CurrentAdmin, DbDep
from app.services.uploads import save_upload

router = APIRouter(prefix="/admin/uploads", tags=["admin"])


@router.post("", response_model=dict)
async def upload_image(
    file: UploadFile,
    db: DbDep,
    admin: CurrentAdmin,
    purpose: str = "products",
):
    url = await save_upload(file, purpose)
    return {"url": url}
