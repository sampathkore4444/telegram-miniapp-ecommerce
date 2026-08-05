from fastapi import APIRouter

from app.api.deps import CurrentUser, DbDep
from app.core.errors import NotFoundError
from app.models import UserAddress
from app.schemas.address import AddressCreate, AddressPublic, AddressUpdate

router = APIRouter(prefix="/addresses", tags=["addresses"])


async def _clear_default(db: DbDep, user_id: int, keep_id: int | None = None) -> None:
    from sqlalchemy import update

    stmt = update(UserAddress).where(
        UserAddress.user_id == user_id,
        UserAddress.is_default.is_(True),
    )
    if keep_id is not None:
        stmt = stmt.where(UserAddress.id != keep_id)
    await db.execute(stmt.values(is_default=False))


async def _get_own(db: DbDep, user_id: int, address_id: int) -> UserAddress:
    address = await db.get(UserAddress, address_id)
    if address is None or address.user_id != user_id:
        raise NotFoundError("Address not found")
    return address


async def _list(user_id: int, db: DbDep) -> list[dict]:
    from sqlalchemy import select

    result = await db.execute(
        select(UserAddress)
        .where(UserAddress.user_id == user_id)
        .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
    )
    return [a.to_dict() for a in result.scalars().all()]


@router.get("", response_model=dict)
async def list_addresses(user: CurrentUser, db: DbDep):
    return {"items": await _list(user.id, db)}


@router.post("", response_model=AddressPublic)
async def create_address(payload: AddressCreate, user: CurrentUser, db: DbDep):
    from sqlalchemy import select

    count = (
        await db.execute(select(UserAddress.id).where(UserAddress.user_id == user.id))
    ).scalars().first()
    is_default = payload.is_default or count is None
    if is_default:
        await _clear_default(db, user.id)
    address = UserAddress(
        user_id=user.id,
        label=payload.label,
        recipient_name=payload.recipient_name,
        recipient_phone=payload.recipient_phone,
        address=payload.address,
        is_default=is_default,
    )
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address.to_dict()


@router.patch("/{address_id}", response_model=AddressPublic)
async def update_address(
    address_id: int, payload: AddressUpdate, user: CurrentUser, db: DbDep
):
    address = await _get_own(db, user.id, address_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_default"):
        await _clear_default(db, user.id, keep_id=address.id)
    for key, value in data.items():
        setattr(address, key, value)
    await db.commit()
    await db.refresh(address)
    return address.to_dict()


@router.delete("/{address_id}", response_model=dict)
async def delete_address(address_id: int, user: CurrentUser, db: DbDep):
    address = await _get_own(db, user.id, address_id)
    was_default = address.is_default
    await db.delete(address)
    await db.flush()
    if was_default:
        from sqlalchemy import select

        other = (
            await db.execute(
                select(UserAddress).where(UserAddress.user_id == user.id)
            )
        ).scalars().first()
        if other is not None:
            other.is_default = True
    await db.commit()
    return {"items": await _list(user.id, db)}
