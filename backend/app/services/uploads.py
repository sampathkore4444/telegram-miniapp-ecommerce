import secrets
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

# Sub-directories by purpose.
PURPOSES = {"products", "receipts", "store"}


def _ensure_dir(subdir: str) -> Path:
    base = Path(settings.UPLOAD_DIR)
    target = base / subdir
    target.mkdir(parents=True, exist_ok=True)
    return target


def validate_image(file: UploadFile) -> None:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise AppError(
            "Unsupported file type. Allowed: JPG, PNG, WEBP, GIF.",
            code="invalid_file_type",
        )
    if file.size and file.size > settings.max_upload_bytes:
        raise AppError(
            f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB}MB.",
            code="file_too_large",
        )


async def save_upload(file: UploadFile, subdir: str = "products") -> str:
    """Persist an uploaded image and return its public URL path."""
    if subdir not in PURPOSES:
        raise AppError("Invalid upload purpose.", code="invalid_upload_purpose")
    validate_image(file)
    target_dir = _ensure_dir(subdir)
    ext = ALLOWED_CONTENT_TYPES[file.content_type or ""]
    name = f"{uuid.uuid4().hex}{ext}"
    destination = target_dir / name

    size = 0
    with destination.open("wb") as out:
        while chunk := await file.read(1024 * 256):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                destination.unlink(missing_ok=True)
                raise AppError(
                    f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB}MB.",
                    code="file_too_large",
                )
            out.write(chunk)

    return f"/uploads/{subdir}/{name}"
