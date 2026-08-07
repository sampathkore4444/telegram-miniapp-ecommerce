from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import ActiveStore, CurrentUser, DbDep
from app.core.errors import PermissionError
from app.core.plans import feature_enabled
from app.models import CartItem, DiscountType
from app.schemas.discount import DiscountCheckResponse
from app.services.orders import validate_coupon
from app.services.pricing import line_subtotal
from app.services.plans import get_store_plan

router = APIRouter(prefix="/coupons", tags=["coupons"])


class CouponCheckRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)


@router.post("/check", response_model=DiscountCheckResponse)
async def check_coupon(payload: CouponCheckRequest, user: CurrentUser, db: DbDep, store: ActiveStore):
    """Validate a coupon against the current user's cart and report the discount."""
    plan = await get_store_plan(db, store)
    if not feature_enabled(plan, "coupons"):
        raise PermissionError(
            "Coupons are not enabled on this store's plan.", code="plan_required"
        )
    from sqlalchemy import select

    result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.store_id == store.id
        )
    )
    cart_items = result.scalars().all()
    subtotal = sum(
        (line_subtotal(item.product, item.variant, item.quantity) for item in cart_items),
        Decimal("0"),
    )
    coupon = await validate_coupon(
        db, payload.code, user, subtotal=subtotal, store_id=store.id
    )

    if coupon.discount_type == DiscountType.PERCENT:
        discount = (subtotal * Decimal(str(coupon.value))) / Decimal("100")
        message = f"{coupon.code} applied — {coupon.value:g}% off (save {float(discount):.2f})."
    else:
        discount = min(Decimal(str(coupon.value)), subtotal)
        message = f"{coupon.code} applied — you save {float(discount):.2f}."
    discount = min(discount, subtotal)

    return DiscountCheckResponse(
        code=coupon.code,
        discount_type=coupon.discount_type,
        value=float(coupon.value),
        discount_amount=float(discount),
        min_subtotal=float(coupon.min_subtotal),
        message=message,
    )
