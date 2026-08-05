from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.admin import categories as admin_categories
from app.api.admin import broadcasts as admin_broadcasts
from app.api.admin import coupons as admin_coupons
from app.api.admin import customers as admin_customers
from app.api.admin import dashboard as admin_dashboard
from app.api.admin import orders as admin_orders
from app.api.admin import products as admin_products
from app.api.admin import reviews as admin_reviews
from app.api.admin import settings as admin_settings
from app.api.admin import uploads as admin_uploads
from app.api import (
    addresses,
    auth,
    cart,
    categories,
    coupons,
    health,
    orders,
    products,
    reviews,
    store,
    users,
    wishlist,
)
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def _cart_reminder_loop() -> None:
    """Periodically nudge buyers with stale carts. Best-effort; never raises."""
    while True:
        await asyncio.sleep(settings.CART_REMINDER_INTERVAL_SECONDS)
        if not settings.CART_REMINDER_ENABLED:
            continue
        try:
            from app.services.reminders import send_abandoned_cart_reminders

            async with AsyncSessionLocal() as db:
                sent = await send_abandoned_cart_reminders(db)
                if sent:
                    await db.commit()
        except Exception as exc:  # noqa: BLE001 - reminders must never break requests
            logger.warning("cart reminder task error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cart_reminder_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/docs" if settings.is_dev else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(addresses.router, prefix="/api")
    app.include_router(categories.router, prefix="/api")
    app.include_router(products.router, prefix="/api")
    app.include_router(store.router, prefix="/api")
    app.include_router(cart.router, prefix="/api")
    app.include_router(orders.router, prefix="/api")
    app.include_router(coupons.router, prefix="/api")
    app.include_router(wishlist.router, prefix="/api")
    app.include_router(reviews.router, prefix="/api")
    app.include_router(admin_dashboard.router, prefix="/api")
    app.include_router(admin_products.router, prefix="/api")
    app.include_router(admin_categories.router, prefix="/api")
    app.include_router(admin_orders.router, prefix="/api")
    app.include_router(admin_settings.router, prefix="/api")
    app.include_router(admin_uploads.router, prefix="/api")
    app.include_router(admin_coupons.router, prefix="/api")
    app.include_router(admin_reviews.router, prefix="/api")
    app.include_router(admin_customers.router, prefix="/api")
    app.include_router(admin_broadcasts.router, prefix="/api")

    # Uploaded files (public)
    from pathlib import Path

    uploads_dir = Path(settings.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    # SPA static frontend
    class SPAStaticFiles(StaticFiles):
        def file_response(self, *args, **kwargs):
            response = super().file_response(*args, **kwargs)
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
            return response

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.exists():
        app.mount("/", SPAStaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


app = create_app()
