from fastapi import APIRouter

from app.api.deps import DbDep
from app.core.errors import NotFoundError
from app.models import Category, Product
from app.schemas.catalog import CategoryPublic

router = APIRouter(prefix="/categories", tags=["catalog"])


def _category_public(cat: Category, count: int = 0) -> CategoryPublic:
    return CategoryPublic(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        description=cat.description,
        image_url=cat.image_url,
        sort_order=cat.sort_order,
        is_active=cat.is_active,
        product_count=count,
    )


@router.get("", response_model=list[CategoryPublic])
async def list_categories(db: DbDep, include_inactive: bool = False):
    from sqlalchemy import func, select

    stmt = (
        select(Category, func.count(Product.id).label("cnt"))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.sort_order, Category.name)
    )
    if not include_inactive:
        stmt = stmt.where(Category.is_active.is_(True))
    result = await db.execute(stmt)
    return [_category_public(cat, cnt) for cat, cnt in result.all()]


@router.get("/{slug}", response_model=CategoryPublic)
async def get_category(slug: str, db: DbDep):
    from sqlalchemy import select

    result = await db.execute(select(Category).where(Category.slug == slug))
    cat = result.scalar_one_or_none()
    if cat is None:
        raise NotFoundError("Category not found")
    return _category_public(cat)
