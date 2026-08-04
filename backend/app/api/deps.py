import time
from collections import defaultdict
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, PermissionError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, UserRole

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise PermissionError("Missing or malformed Authorization header", code="unauthorized")
    return auth[7:].strip()


async def get_current_user(request: Request, db: DbDep) -> User:
    token = _bearer_token(request)
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", "0"))
    except (jwt.PyJWTError, ValueError) as exc:
        raise PermissionError("Invalid or expired token", code="unauthorized") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise PermissionError("User not found or inactive", code="unauthorized")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionError("Admin access required", code="admin_required")
    return user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]


# --- Simple in-memory sliding-window rate limiter (per client) ---
_hits: dict[str, list[float]] = defaultdict(list)


def reset_rate_limits() -> None:
    """Clear all rate-limit state (used by tests)."""
    _hits.clear()


def rate_limit(max_requests: int | None = None, window: int | None = None) -> Callable:
    limit = max_requests or settings.RATE_LIMIT_MAX
    window_s = window or settings.RATE_LIMIT_WINDOW_SECONDS

    async def dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        now = time.monotonic()
        bucket = _hits[key]
        while bucket and now - bucket[0] > window_s:
            bucket.pop(0)
        if len(bucket) >= limit:
            raise AppError(
                "Too many requests. Please try again later.",
                code="rate_limited",
                status_code=429,
            )
        bucket.append(now)

    return dependency
