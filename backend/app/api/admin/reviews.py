from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import AdminStore, DbDep
from app.core.errors import NotFoundError
from app.models import Product, ProductReview
from app.schemas.common import Page
from app.schemas.review import ReviewModerate, ReviewPublic

router = APIRouter(prefix="/admin/reviews", tags=["admin"])


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


@router.get("", response_model=Page[dict])
async def admin_list_reviews(
    db: DbDep,
    store: AdminStore,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(approved|hidden|all)$"),
    search: str | None = None,
):
    stmt = select(ProductReview).where(ProductReview.store_id == store.id)
    if status == "approved":
        stmt = stmt.where(ProductReview.is_approved.is_(True))
    elif status == "hidden":
        stmt = stmt.where(ProductReview.is_approved.is_(False))
    if search:
        stmt = stmt.where(ProductReview.comment.ilike(f"%{search.strip()}%"))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    pages = (total + page_size - 1) // page_size
    result = await db.execute(
        stmt.order_by(ProductReview.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for r in result.scalars().all():
        d = _to_public(r).model_dump(mode="json")
        product = await db.get(Product, r.product_id)
        d["product_name"] = product.name if product else None
        items.append(d)
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.patch("/{review_id}", response_model=dict)
async def admin_moderate_review(
    review_id: int, payload: ReviewModerate, db: DbDep, store: AdminStore
):
    review = await db.get(ProductReview, review_id)
    if review is None or review.store_id != store.id:
        raise NotFoundError("Review not found")
    review.is_approved = payload.is_approved
    await db.commit()
    await db.refresh(review)
    return _to_public(review).model_dump(mode="json")


@router.delete("/{review_id}", status_code=204)
async def admin_delete_review(review_id: int, db: DbDep, store: AdminStore):
    review = await db.get(ProductReview, review_id)
    if review is None or review.store_id != store.id:
        raise NotFoundError("Review not found")
    await db.delete(review)
    await db.commit()
