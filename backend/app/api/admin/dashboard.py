import datetime as dt
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import AdminStore, DbDep
from app.core.plans import feature_enabled
from app.models import (
    Category,
    DiscountCode,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    User,
)
from app.schemas.settings import DashboardStats

router = APIRouter(prefix="/admin/dashboard", tags=["admin"])

PAID_STATUSES = {OrderStatus.COMPLETED, OrderStatus.DELIVERED}


def _today_start() -> dt.datetime:
    now = dt.datetime.now(dt.timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("", response_model=DashboardStats)
async def dashboard(db: DbDep, store: AdminStore):
    revenue_stmt = (
        select(func.coalesce(func.sum(Order.total), 0))
        .where(Order.status.in_(PAID_STATUSES), Order.store_id == store.id)
    )
    total_revenue = (await db.execute(revenue_stmt)).scalar() or 0

    total_orders = (
        await db.execute(select(func.count(Order.id)).where(Order.store_id == store.id))
    ).scalar() or 0
    pending_orders = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.store_id == store.id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.PENDING_PAYMENT, OrderStatus.UNDER_REVIEW]),
            )
        )
    ).scalar() or 0
    products_count = (
        await db.execute(select(func.count(Product.id)).where(Product.store_id == store.id))
    ).scalar() or 0
    low_stock_count = (
        await db.execute(
            select(func.count(Product.id)).where(
                Product.store_id == store.id, Product.stock <= 5
            )
        )
    ).scalar() or 0
    customers_count = (
        await db.execute(
            select(func.count(func.distinct(Order.user_id))).where(Order.store_id == store.id)
        )
    ).scalar() or 0

    today_start = _today_start()
    today_revenue = (
        await db.execute(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.status.in_(PAID_STATUSES),
                Order.store_id == store.id,
                Order.created_at >= today_start,
            )
        )
    ).scalar() or 0
    today_orders = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.store_id == store.id, Order.created_at >= today_start
            )
        )
    ).scalar() or 0

    recent = await db.execute(
        select(Order).where(Order.store_id == store.id).order_by(Order.created_at.desc()).limit(8)
    )
    recent_orders = [
        {
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status.value,
            "total": float(o.total),
            "created_at": o.created_at.isoformat(),
            "payment_method": o.payment_method.value,
        }
        for o in recent.scalars().all()
    ]

    top = await db.execute(
        select(
            OrderItem.product_id,
            OrderItem.product_name,
            OrderItem.image_url,
            OrderItem.unit_price,
            func.sum(OrderItem.quantity).label("qty"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.store_id == store.id)
        .group_by(
            OrderItem.product_id,
            OrderItem.product_name,
            OrderItem.image_url,
            OrderItem.unit_price,
        )
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    )
    top_products = []
    for product_id, product_name, image_url, unit_price, qty in top.all():
        product = await db.get(Product, product_id) if product_id else None
        top_products.append(
            {
                "name": product.name if product else product_name,
                "quantity": qty,
                "revenue": float(unit_price) * int(qty),
                "image_url": image_url,
            }
        )

    paid_count = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.status.in_(PAID_STATUSES), Order.store_id == store.id
            )
        )
    ).scalar() or 0
    avg_order_value = (
        Decimal(str(total_revenue)) / paid_count if paid_count else Decimal("0")
    )

    user_order_counts = (
        await db.execute(
            select(Order.user_id, func.count(Order.id))
            .where(Order.store_id == store.id)
            .group_by(Order.user_id)
        )
    ).all()
    total_customers = len(user_order_counts)
    repeat_customers = sum(1 for _, c in user_order_counts if c >= 2)
    repeat_customer_rate = (
        round(repeat_customers / total_customers * 100, 2) if total_customers else 0.0
    )

    cat_rows = await db.execute(
        select(
            func.coalesce(Category.name, "Uncategorized").label("name"),
            func.coalesce(func.sum(OrderItem.total), 0).label("rev"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .outerjoin(Category, Category.id == Product.category_id)
        .where(Order.status.in_(PAID_STATUSES), Order.store_id == store.id)
        .group_by(Category.name)
        .order_by(func.sum(OrderItem.total).desc())
    )
    revenue_by_category = [
        {"name": name, "revenue": float(rev or 0)} for name, rev in cat_rows.all()
    ]

    coupon_rows = await db.execute(
        select(DiscountCode.code, DiscountCode.used_count)
        .where(DiscountCode.store_id == store.id, DiscountCode.used_count > 0)
        .order_by(DiscountCode.used_count.desc())
    )
    coupon_redemptions = [
        {"code": code, "redemptions": count} for code, count in coupon_rows.all()
    ]

    total_discount = (
        await db.execute(
            select(func.coalesce(func.sum(Order.discount), 0)).where(
                Order.status.in_(PAID_STATUSES), Order.store_id == store.id
            )
        )
    ).scalar() or 0

    # Sales for last 14 days grouped by day
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=13)
    since_start = since.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = await db.execute(
        select(func.date(Order.created_at).label("day"), func.sum(Order.total).label("rev"))
        .where(
            Order.status.in_(PAID_STATUSES),
            Order.store_id == store.id,
            Order.created_at >= since_start,
        )
        .group_by("day")
        .order_by("day")
    )
    by_day = {str(day): float(rev or 0) for day, rev in rows.all()}
    sales_last_14_days = [
        {
            "day": (since_start + dt.timedelta(days=i)).strftime("%Y-%m-%d"),
            "revenue": by_day.get((since_start + dt.timedelta(days=i)).strftime("%Y-%m-%d"), 0.0),
        }
        for i in range(14)
    ]

    status_counts = await db.execute(
        select(Order.status, func.count(Order.id))
        .where(Order.store_id == store.id)
        .group_by(Order.status)
    )
    orders_by_status = {s.value if hasattr(s, "value") else str(s): c for s, c in status_counts.all()}

    plan = store.owner.plan
    has_analytics = feature_enabled(plan, "analytics")
    has_coupons = feature_enabled(plan, "coupons")

    return DashboardStats(
        total_revenue=total_revenue,
        total_orders=total_orders,
        pending_orders=pending_orders,
        products_count=products_count,
        low_stock_count=low_stock_count,
        customers_count=customers_count,
        today_revenue=today_revenue,
        today_orders=today_orders,
        recent_orders=recent_orders,
        top_products=top_products if has_analytics else [],
        sales_last_14_days=sales_last_14_days if has_analytics else [],
        orders_by_status=orders_by_status,
        avg_order_value=avg_order_value if has_analytics else 0,
        repeat_customer_rate=repeat_customer_rate if has_analytics else 0.0,
        revenue_by_category=revenue_by_category if has_analytics else [],
        coupon_redemptions=coupon_redemptions if has_coupons else [],
        total_discount_given=total_discount if has_coupons else 0,
    )
