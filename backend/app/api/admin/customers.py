from fastapi import APIRouter, Query
from fastapi.responses import Response
from sqlalchemy import func, or_, select

from app.api.deps import AdminStore, DbDep
from app.core.errors import NotFoundError
from app.models import Order, OrderStatus, User
from app.schemas.customer import CustomerDetail, CustomerUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/admin/customers", tags=["admin"])

PAID_STATUSES = {OrderStatus.COMPLETED, OrderStatus.DELIVERED}


async def _aggregates(db: DbDep, store_id: int) -> tuple[dict[int, int], dict[int, float], dict[int, str]]:
    count_rows = await db.execute(
        select(Order.user_id, func.count(Order.id))
        .where(Order.store_id == store_id)
        .group_by(Order.user_id)
    )
    order_counts = {uid: int(c) for uid, c in count_rows.all()}

    spent_rows = await db.execute(
        select(
            Order.user_id,
            func.coalesce(func.sum(Order.total), 0),
            func.max(Order.created_at),
        )
        .where(Order.status.in_(PAID_STATUSES), Order.store_id == store_id)
        .group_by(Order.user_id)
    )
    rows = spent_rows.all()
    spent = {uid: float(s) for uid, s, _ in rows}
    last_order = {uid: str(ts) for uid, _, ts in rows}
    return order_counts, spent, last_order


def _to_public(user: User, order_counts, spent, last_order) -> dict:
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": user.display_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "phone": user.phone,
        "note": user.note,
        "orders_count": order_counts.get(user.id, 0),
        "total_spent": spent.get(user.id, 0.0),
        "last_order_at": last_order.get(user.id),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("", response_model=Page[dict])
async def admin_list_customers(
    db: DbDep,
    store: AdminStore,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    is_active: bool | None = None,
):
    stmt = select(User).where(User.role != "admin")
    if search:
        term = search.strip()
        stmt = stmt.where(
            or_(
                User.username.ilike(f"%{term}%"),
                User.first_name.ilike(f"%{term}%"),
                User.last_name.ilike(f"%{term}%"),
                User.phone.ilike(f"%{term}%"),
            )
        )
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    pages = (total + page_size - 1) // page_size
    result = await db.execute(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    order_counts, spent, last_order = await _aggregates(db, store.id)
    items = [_to_public(u, order_counts, spent, last_order) for u in users]
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)


CUSTOMERS_CSV_HEADERS = [
    "telegram_id",
    "display_name",
    "username",
    "first_name",
    "last_name",
    "phone",
    "is_active",
    "orders_count",
    "total_spent",
    "last_order_at",
    "created_at",
]


@router.get("/export", response_model=None)
async def admin_export_customers(db: DbDep, store: AdminStore):
    """Download every buyer as CSV."""
    import csv
    import io

    result = await db.execute(select(User).where(User.role != "admin").order_by(User.id))
    users = result.scalars().all()
    order_counts, spent, last_order = await _aggregates(db, store.id)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CUSTOMERS_CSV_HEADERS)
    writer.writeheader()
    for u in users:
        writer.writerow(
            {
                "telegram_id": u.telegram_id,
                "display_name": u.display_name,
                "username": u.username or "",
                "first_name": u.first_name or "",
                "last_name": u.last_name or "",
                "phone": u.phone or "",
                "is_active": "1" if u.is_active else "0",
                "orders_count": order_counts.get(u.id, 0),
                "total_spent": spent.get(u.id, 0.0),
                "last_order_at": last_order.get(u.id, ""),
                "created_at": u.created_at.isoformat() if u.created_at else "",
            }
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="customers_export.csv"'},
    )


@router.get("/{customer_id}", response_model=CustomerDetail)
async def admin_get_customer(customer_id: int, db: DbDep, store: AdminStore):
    user = await db.get(User, customer_id)
    if user is None or user.role.value == "admin":
        raise NotFoundError("Customer not found")

    result = await db.execute(
        select(Order)
        .where(Order.user_id == user.id, Order.store_id == store.id)
        .order_by(Order.created_at.desc())
        .limit(50)
    )
    orders = result.scalars().all()
    order_counts, spent, last_order = await _aggregates(db, store.id)
    base = _to_public(user, order_counts, spent, last_order)
    base["orders"] = [
        {
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status.value,
            "payment_method": o.payment_method.value,
            "total": float(o.total),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]
    return CustomerDetail(**base)


@router.patch("/{customer_id}", response_model=dict)
async def admin_update_customer(
    customer_id: int, payload: CustomerUpdate, db: DbDep, store: AdminStore
):
    user = await db.get(User, customer_id)
    if user is None or user.role.value == "admin":
        raise NotFoundError("Customer not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    order_counts, spent, last_order = await _aggregates(db, store.id)
    return _to_public(user, order_counts, spent, last_order)
