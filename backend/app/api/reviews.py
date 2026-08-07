from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import ActiveStore, CurrentUser, DbDep
from app.core.errors import AppError, NotFoundError
from app.models import Product, ProductReview
from app.schemas.review import ReviewCreate, ReviewPublic

router = APIRouter(prefix="/products/{product_id}/reviews", tags=["reviews"])


def _to_public(r: ProductReview) -> ReviewPublic:
    return ReviewPublic(
        id=r.id,
        product_id=r.product_id,
        rating=r.rating,
        comment=r.comment,
        images=r.images or [],
        user_id=r.user_id,
        user_name=r.user.display_name if r.user else "Anonymous",
        created_at=r.created_at,
    )


@router.get("", response_model=dict)
async def list_product_reviews(product_id: int, db: DbDep, store: ActiveStore):
    product = await db.get(Product, product_id)
    if product is None or product.store_id != store.id:
        raise NotFoundError("Product not found")

    base = select(ProductReview).where(
        ProductReview.product_id == product_id, ProductReview.is_approved.is_(True)
    )
    result = await db.execute(base.order_by(ProductReview.created_at.desc()))
    reviews = result.scalars().all()

    summary_row = (
        await db.execute(
            select(
                func.count(ProductReview.id),
                func.coalesce(func.avg(ProductReview.rating), 0),
            ).where(
                ProductReview.product_id == product_id,
                ProductReview.is_approved.is_(True),
            )
        )
    ).one()
    count, avg = summary_row

    distribution = {str(i): 0 for i in range(1, 6)}
    for r in reviews:
        distribution[str(r.rating)] = distribution.get(str(r.rating), 0) + 1

    return {
        "summary": {
            "average": round(float(avg), 1),
            "count": int(count),
            "distribution": distribution,
        },
        "items": [_to_public(r).model_dump(mode="json") for r in reviews],
    }


@router.post("", response_model=dict)
async def submit_review(
    product_id: int, payload: ReviewCreate, user: CurrentUser, db: DbDep, store: ActiveStore
):
    product = await db.get(Product, product_id)
    if product is None or product.status != "active" or product.store_id != store.id:
        raise NotFoundError("Product not found")

    result = await db.execute(
        select(ProductReview).where(
            ProductReview.user_id == user.id, ProductReview.product_id == product_id
        )
    )
    if result.scalar_one_or_none() is not None:
        raise AppError("You have already reviewed this product.", code="already_reviewed")

    review = ProductReview(
        user_id=user.id,
        product_id=product_id,
        store_id=store.id,
        rating=payload.rating,
        comment=payload.comment,
        images=payload.images or [],
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return _to_public(review).model_dump(mode="json")
