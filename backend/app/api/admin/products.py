from fastapi import APIRouter, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentAdmin, DbDep
from app.core.errors import ConflictError, NotFoundError
from app.models import Category, Product, ProductVariant
from app.schemas.catalog import ProductCreate, ProductUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/admin/products", tags=["admin"])


async def _get_product(db: DbDep, product_id: int) -> Product | None:
    stmt = (
        select(Product)
        .options(selectinload(Product.variants))
        .where(Product.id == product_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _admin_product_dict(product: Product) -> dict:
    d = product.to_public_dict()
    d["status"] = product.status.value
    d["variants"] = [v.to_public_dict() for v in product.variants]
    return d


async def _sync_variants(db: DbDep, product: Product, variants: list) -> None:
    result = await db.execute(
        select(ProductVariant).where(ProductVariant.product_id == product.id)
    )
    existing = {v.id: v for v in result.scalars().all()}
    provided_ids = {v.id for v in variants if v.id is not None}
    for vid, v in existing.items():
        if vid not in provided_ids:
            await db.delete(v)
    for v in variants:
        if v.id is not None and v.id in existing:
            ex = existing[v.id]
            ex.name = v.name
            ex.options = v.options or {}
            ex.price = v.price
            ex.compare_at_price = v.compare_at_price
            ex.sku = v.sku
            ex.stock = v.stock
            ex.is_active = v.is_active
        else:
            db.add(
                ProductVariant(
                    product_id=product.id,
                    name=v.name,
                    options=v.options or {},
                    price=v.price,
                    compare_at_price=v.compare_at_price,
                    sku=v.sku,
                    stock=v.stock,
                    is_active=v.is_active,
                )
            )


async def _trigger_restock_alerts(
    db: DbDep,
    product: Product,
    old_stock: int,
    old_variant_stocks: dict[int, int],
    variants: list[ProductVariant],
) -> None:
    """Fire back-in-stock alerts for anything that moved from 0 to >0 stock."""
    from app.services.stock_alerts import trigger_stock_alerts

    if old_stock == 0 and product.stock > 0:
        await trigger_stock_alerts(db, product)
    for v in variants:
        if old_variant_stocks.get(v.id, 0) == 0 and v.stock > 0:
            await trigger_stock_alerts(db, product, v)


def _slugify(name: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "product"


async def _unique_slug(db: DbDep, name: str, exclude_id: int | None = None) -> str:
    base = _slugify(name)
    candidate = base
    counter = 1
    while True:
        stmt = select(Product).where(Product.slug == candidate)
        if exclude_id:
            stmt = stmt.where(Product.id != exclude_id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            return candidate
        counter += 1
        candidate = f"{base}-{counter}"


@router.get("", response_model=Page[dict])
async def admin_list_products(
    db: DbDep,
    admin: CurrentAdmin,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    category_id: int | None = None,
    status: str | None = None,
    low_stock: bool = False,
):
    stmt = select(Product)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search.strip()}%"))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if status:
        stmt = stmt.where(Product.status == status)
    if low_stock:
        stmt = stmt.where(Product.stock <= 5)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    pages = (total + page_size - 1) // page_size
    result = await db.execute(
        stmt.options(selectinload(Product.variants))
        .order_by(Product.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    products = []
    for p in result.scalars().all():
        d = p.to_public_dict()
        d["status"] = p.status.value
        products.append(d)
    return Page(items=products, total=total, page=page, page_size=page_size, pages=pages)


CSV_HEADERS = ["name", "price", "compare_at_price", "category", "sku", "stock", "is_featured", "status", "description"]


def _csv_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


@router.get("/export", response_model=None)
async def admin_export_products(db: DbDep, admin: CurrentAdmin):
    """Download the full catalog as CSV."""
    import csv
    import io

    result = await db.execute(select(Product).order_by(Product.id))
    products = result.scalars().all()

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_HEADERS)
    writer.writeheader()
    for p in products:
        writer.writerow(
            {
                "name": p.name,
                "price": _csv_value(p.price),
                "compare_at_price": _csv_value(p.compare_at_price),
                "category": p.category.name if p.category else "",
                "sku": _csv_value(p.sku),
                "stock": _csv_value(p.stock),
                "is_featured": _csv_value(p.is_featured),
                "status": p.status.value if p.status else "",
                "description": _csv_value(p.description),
            }
        )

    filename = "products_export.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _category_by_name(db: DbDep, name: str) -> Category | None:
    if not name:
        return None
    result = await db.execute(select(Category).where(Category.name == name))
    category = result.scalar_one_or_none()
    if category is not None:
        return category
    slug = _slugify(name)
    candidate = slug
    counter = 1
    while True:
        dup = await db.execute(select(Category).where(Category.slug == candidate))
        if dup.scalar_one_or_none() is None:
            break
        counter += 1
        candidate = f"{slug}-{counter}"
    category = Category(name=name, slug=candidate)
    db.add(category)
    await db.flush()
    return category


@router.post("/import", response_model=dict)
async def admin_import_products(file: UploadFile, db: DbDep, admin: CurrentAdmin):
    """Import products from a CSV file. Upserts by SKU, then by exact name."""
    import csv
    import io

    if not (file.filename or "").lower().endswith(".csv"):
        raise ConflictError("Please upload a .csv file.")

    raw = await file.read()
    if not raw.strip():
        raise ConflictError("The uploaded file is empty.")

    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or "name" not in reader.fieldnames or "price" not in reader.fieldnames:
        raise ConflictError('CSV must contain at least "name" and "price" columns.')

    created = 0
    updated = 0
    skipped = 0
    restocked: list[Product] = []

    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            skipped += 1
            continue

        def _num(key):
            val = (row.get(key) or "").strip()
            if not val:
                return None
            try:
                return float(val)
            except ValueError:
                raise ConflictError(f'Invalid number "{val}" in column "{key}" for product "{name}".')

        price = _num("price")
        if price is None or price <= 0:
            skipped += 1
            continue

        sku = (row.get("sku") or "").strip() or None
        existing = None
        if sku:
            res = await db.execute(select(Product).where(Product.sku == sku))
            existing = res.scalar_one_or_none()
        if existing is None:
            res = await db.execute(select(Product).where(Product.name == name))
            existing = res.scalar_one_or_none()

        category = await _category_by_name(db, (row.get("category") or "").strip())

        stock_val = (row.get("stock") or "0").strip()
        try:
            stock = int(float(stock_val))
        except ValueError:
            stock = 0
        status = (row.get("status") or "active").strip().lower()
        if status not in {"active", "draft", "archived"}:
            status = "active"
        compare = _num("compare_at_price")
        is_featured = (row.get("is_featured") or "").strip() in {"1", "true", "True", "yes", "y"}

        data = {
            "name": name,
            "price": price,
            "compare_at_price": compare,
            "category_id": category.id if category else None,
            "sku": sku,
            "stock": stock,
            "is_featured": is_featured,
            "status": status,
            "description": (row.get("description") or "").strip() or None,
        }

        if existing is not None:
            old_stock = existing.stock
            for key, value in data.items():
                setattr(existing, key, value)
            if old_stock == 0 and existing.stock > 0:
                restocked.append(existing)
            updated += 1
        else:
            slug = await _unique_slug(db, name)
            db.add(Product(**data, slug=slug))
            created += 1

    await db.commit()

    from app.services.stock_alerts import trigger_stock_alerts

    for product in restocked:
        await trigger_stock_alerts(db, product)
    await db.commit()

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "total": created + updated + skipped,
    }


@router.get("/{product_id}", response_model=dict)
async def admin_get_product(product_id: int, db: DbDep, admin: CurrentAdmin):
    product = await _get_product(db, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    return _admin_product_dict(product)


@router.post("", response_model=dict)
async def admin_create_product(payload: ProductCreate, db: DbDep, admin: CurrentAdmin):
    if payload.category_id:
        cat = await db.get(Category, payload.category_id)
        if cat is None:
            raise NotFoundError("Category not found")
    slug = payload.slug or await _unique_slug(db, payload.name)
    data = payload.model_dump(exclude={"slug", "variants"})
    product = Product(**data, slug=slug)
    db.add(product)
    await db.flush()
    await _sync_variants(db, product, payload.variants)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise ConflictError("A product with this slug already exists.")
    product = await _get_product(db, product.id)
    return _admin_product_dict(product)


@router.patch("/{product_id}", response_model=dict)
async def admin_update_product(
    product_id: int, payload: ProductUpdate, db: DbDep, admin: CurrentAdmin
):
    product = await _get_product(db, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    data = payload.model_dump(exclude_unset=True, exclude={"variants"})
    variants = payload.variants
    if "category_id" in data and data["category_id"] is not None:
        cat = await db.get(Category, data["category_id"])
        if cat is None:
            raise NotFoundError("Category not found")
    slug = data.pop("slug", None)
    if slug is None and data.get("name"):
        slug = await _unique_slug(db, data["name"], exclude_id=product.id)
    if slug:
        data["slug"] = slug

    old_stock = product.stock
    old_variant_stocks = {v.id: v.stock for v in product.variants}

    for key, value in data.items():
        setattr(product, key, value)
    if variants is not None:
        await _sync_variants(db, product, variants)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise ConflictError("Could not save product.")
    await db.refresh(product, ["variants"])
    await _trigger_restock_alerts(
        db, product, old_stock, old_variant_stocks, product.variants
    )
    await db.commit()
    return _admin_product_dict(product)


@router.delete("/{product_id}", status_code=204)
async def admin_delete_product(product_id: int, db: DbDep, admin: CurrentAdmin):
    product = await db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    await db.delete(product)
    await db.commit()
