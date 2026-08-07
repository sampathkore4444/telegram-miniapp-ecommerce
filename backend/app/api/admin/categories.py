from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import AdminStore, DbDep
from app.core.errors import ConflictError, NotFoundError
from app.models import Category, Product
from app.schemas.catalog import CategoryCreate, CategoryPublic, CategoryUpdate

router = APIRouter(prefix="/admin/categories", tags=["admin"])


def _slugify(name: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "category"


def _public(cat: Category, count: int = 0) -> CategoryPublic:
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


async def _unique_slug(
    db: DbDep, name: str, store_id: int, exclude_id: int | None = None
) -> str:
    base = _slugify(name)
    candidate = base
    counter = 1
    while True:
        stmt = select(Category).where(
            Category.slug == candidate, Category.store_id == store_id
        )
        if exclude_id:
            stmt = stmt.where(Category.id != exclude_id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            return candidate
        counter += 1
        candidate = f"{base}-{counter}"


@router.get("", response_model=list[CategoryPublic])
async def admin_list_categories(db: DbDep, store: AdminStore):
    stmt = (
        select(Category, func.count(Product.id).label("cnt"))
        .outerjoin(Product, Product.category_id == Category.id)
        .where(Category.store_id == store.id)
        .group_by(Category.id)
        .order_by(Category.sort_order, Category.name)
    )
    result = await db.execute(stmt)
    return [_public(cat, cnt) for cat, cnt in result.all()]


@router.post("", response_model=CategoryPublic)
async def admin_create_category(payload: CategoryCreate, db: DbDep, store: AdminStore):
    slug = payload.slug or await _unique_slug(db, payload.name, store.id)
    cat = Category(
        **payload.model_dump(exclude={"slug"}), slug=slug, store_id=store.id
    )
    db.add(cat)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise ConflictError("A category with this slug already exists.")
    await db.refresh(cat)
    return _public(cat)


@router.patch("/{category_id}", response_model=CategoryPublic)
async def admin_update_category(
    category_id: int, payload: CategoryUpdate, db: DbDep, store: AdminStore
):
    cat = await db.get(Category, category_id)
    if cat is None or cat.store_id != store.id:
        raise NotFoundError("Category not found")
    data = payload.model_dump(exclude_unset=True)
    slug = data.pop("slug", None)
    if slug is None and data.get("name"):
        slug = await _unique_slug(db, data["name"], store.id, exclude_id=cat.id)
    if slug:
        data["slug"] = slug
    for key, value in data.items():
        setattr(cat, key, value)
    await db.commit()
    await db.refresh(cat)
    cnt = (
        await db.execute(select(func.count(Product.id)).where(Product.category_id == cat.id))
    ).scalar() or 0
    return _public(cat, cnt)


@router.delete("/{category_id}", status_code=204)
async def admin_delete_category(category_id: int, db: DbDep, store: AdminStore):
    cat = await db.get(Category, category_id)
    if cat is None or cat.store_id != store.id:
        raise NotFoundError("Category not found")
    await db.delete(cat)
    await db.commit()
