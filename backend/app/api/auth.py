from fastapi import APIRouter, Depends, status

from app.api.deps import DbDep, rate_limit
from app.core.config import settings
from app.core.errors import AppError
from app.core.plans import Plan
from app.core.security import create_access_token
from app.core.telegram import TelegramAuthError, extract_user, validate_init_data
from app.models import User, UserRole
from app.schemas.user import AuthResponse, TelegramLoginRequest, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


async def _upsert_user(db: DbDep, telegram_id: int, data: dict) -> User:
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    role = UserRole.ADMIN if telegram_id in settings.admin_ids else UserRole.BUYER
    if user is None:
        user = User(telegram_id=telegram_id, role=role, **{
            k: v for k, v in data.items() if k in {"username", "first_name", "last_name", "photo_url"}
        })
        db.add(user)
    else:
        for k in ("username", "first_name", "last_name", "photo_url"):
            if data.get(k):
                setattr(user, k, data[k])
        if role != user.role:
            user.role = role
    await db.flush()
    return user


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        token=create_access_token(user.id, user.role.value),
        user=UserPublic.model_validate(user),
    )


@router.post("/telegram", response_model=AuthResponse, dependencies=[Depends(rate_limit(20))])
async def telegram_login(payload: TelegramLoginRequest, db: DbDep):
    try:
        parsed = validate_init_data(payload.init_data)
        user_data = extract_user(parsed)
    except TelegramAuthError as exc:
        raise AppError(str(exc), code="invalid_init_data", status_code=status.HTTP_401_UNAUTHORIZED) from exc

    user = await _upsert_user(db, user_data["telegram_id"], user_data)
    if user.is_admin:
        from app.services.stores import ensure_owner_store

        await ensure_owner_store(db, user)
    await db.commit()
    return _auth_response(user)


@router.post("/demo", response_model=AuthResponse, dependencies=[Depends(rate_limit(20))])
async def demo_login(db: DbDep, role: str = "buyer", plan: str = "starter"):
    """Development-only login used to test the app outside Telegram."""
    if not settings.is_dev:
        raise AppError("Demo login is disabled outside development.", code="demo_disabled")

    if role == "admin":
        telegram_id = settings.admin_ids[0] if settings.admin_ids else 1
    else:
        telegram_id = 2
    user = await _upsert_user(
        db,
        telegram_id,
        {
            "username": "demo_admin" if role == "admin" else "demo_buyer",
            "first_name": "Demo" ,
            "last_name": "Owner" if role == "admin" else "Buyer",
        },
    )
    user.role = UserRole.ADMIN if role == "admin" else UserRole.BUYER
    try:
        user.plan = Plan(plan)
    except ValueError:
        raise AppError("Unknown plan", code="invalid_plan")
    if user.is_admin:
        from app.services.stores import ensure_owner_store

        await ensure_owner_store(db, user)
    await db.commit()
    return _auth_response(user)
