import time
from collections import defaultdict
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, PermissionError
from app.core.plans import ensure_feature
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Store, User, UserRole

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


async def get_optional_current_user(request: Request, db: DbDep) -> User | None:
    """Like get_current_user but returns None instead of failing on bad/missing auth."""
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    try:
        payload = decode_access_token(auth[7:].strip())
        user_id = int(payload.get("sub", "0"))
    except (jwt.PyJWTError, ValueError):
        return None
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_current_user)]


async def get_current_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionError("Admin access required", code="admin_required")
    return user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]


def require_feature(feature: str) -> Callable:
    """Admin dependency factory that also requires a plan feature.

    Usage: ``admin: Annotated[User, Depends(require_feature("coupons"))]``
    """

    async def dependency(admin: CurrentAdmin) -> User:
        ensure_feature(admin.plan, feature)
        return admin

    return dependency


# --- Store scoping (multi-store) ---

STORE_SLUG_HEADER = "X-Store-Slug"


async def get_active_store(request: Request, db: DbDep) -> Store:
    """Resolve the store a request targets.

    Uses the ``X-Store-Slug`` header when present; otherwise falls back to the
    deployment's primary store so existing clients/tests keep working.
    """
    from app.services.stores import get_primary_store, get_store_by_slug

    slug = (request.headers.get(STORE_SLUG_HEADER) or "").strip().lower()
    if slug:
        store = await get_store_by_slug(db, slug)
        if store is None:
            raise AppError("Store not found", code="store_not_found", status_code=404)
        return store
    return await get_primary_store(db)


ActiveStore = Annotated[Store, Depends(get_active_store)]


async def get_admin_store(admin: CurrentAdmin, request: Request, db: DbDep) -> Store:
    """Active store that the current admin owns."""
    store = await get_active_store(request, db)
    if store.owner_id != admin.id:
        raise PermissionError("You do not own this store", code="store_forbidden")
    return store


AdminStore = Annotated[Store, Depends(get_admin_store)]


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
