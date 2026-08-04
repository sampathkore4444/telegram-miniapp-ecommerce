from fastapi import APIRouter
from sqlalchemy import delete, select

from app.api.deps import CurrentUser, DbDep
from app.core.errors import AppError, NotFoundError
from app.models import CartItem, Product, ProductVariant
from app.schemas.cart import CartAdd, CartItemPublic, CartPublic, CartUpdate
from app.services.pricing import unit_price_for

router = APIRouter(prefix="/cart", tags=["cart"])


async def _build_cart(db: DbDep, user_id: int) -> CartPublic:
    result = await db.execute(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.created_at.desc())
    )
    items = result.scalars().all()
    public_items = [
        CartItemPublic.from_item(i, float(unit_price_for(i.product, i.variant, i.quantity)))
        for i in items
    ]
    subtotal = round(
        sum(i.unit_price * i.quantity for i in public_items), 2
    )
    return CartPublic(
        items=public_items,
        item_count=sum(i.quantity for i in public_items),
        subtotal=subtotal,
    )


async def _resolve_variant(db: DbDep, product: Product, variant_id: int | None) -> ProductVariant | None:
    if variant_id is None:
        return None
    variant = await db.get(ProductVariant, variant_id)
    if variant is None or variant.product_id != product.id:
        raise NotFoundError("Variant not found")
    return variant


def _available(variant: ProductVariant | None, product: Product) -> int:
    return variant.stock if variant is not None else product.stock


def _label(variant: ProductVariant | None, product: Product) -> str:
    return f"{product.name} ({variant.name})" if variant is not None else product.name


@router.get("", response_model=CartPublic)
async def get_cart(user: CurrentUser, db: DbDep):
    return await _build_cart(db, user.id)


@router.post("/add", response_model=CartPublic)
async def add_to_cart(payload: CartAdd, user: CurrentUser, db: DbDep):
    product = await db.get(Product, payload.product_id)
    if product is None or product.status.value != "active":
        raise NotFoundError("Product not found")
    variant = await _resolve_variant(db, product, payload.variant_id)
    available = _available(variant, product)
    if available < payload.quantity:
        raise AppError(
            f"Only {available} unit(s) of '{_label(variant, product)}' available.",
            code="insufficient_stock",
        )

    result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == user.id,
            CartItem.product_id == payload.product_id,
            CartItem.variant_id == payload.variant_id,
        )
    )
    item = result.scalar_one_or_none()
    if item:
        item.quantity = min(item.quantity + payload.quantity, 99)
        item.reminder_sent_at = None
        if item.quantity > available:
            raise AppError(
                f"Only {available} unit(s) of '{_label(variant, product)}' available.",
                code="insufficient_stock",
            )
    else:
        db.add(
            CartItem(
                user_id=user.id,
                product_id=payload.product_id,
                variant_id=payload.variant_id,
                quantity=payload.quantity,
            )
        )
    await db.commit()
    return await _build_cart(db, user.id)


@router.patch("/{item_id}", response_model=CartPublic)
async def update_cart_item(item_id: int, payload: CartUpdate, user: CurrentUser, db: DbDep):
    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError("Cart item not found")

    if payload.quantity <= 0:
        await db.delete(item)
    else:
        available = _available(item.variant, item.product)
        if payload.quantity > available:
            raise AppError(
                f"Only {available} unit(s) of '{_label(item.variant, item.product)}' available.",
                code="insufficient_stock",
            )
        item.quantity = payload.quantity
        item.reminder_sent_at = None
    await db.commit()
    return await _build_cart(db, user.id)


@router.delete("/{item_id}", response_model=CartPublic)
async def remove_cart_item(item_id: int, user: CurrentUser, db: DbDep):
    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError("Cart item not found")
    await db.delete(item)
    await db.commit()
    return await _build_cart(db, user.id)


@router.delete("", response_model=CartPublic)
async def clear_cart(user: CurrentUser, db: DbDep):
    await db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    await db.commit()
    return await _build_cart(db, user.id)
