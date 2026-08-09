# Telegram Shop — Mini App Ecommerce

A production-grade Telegram Mini App ecommerce store. FastAPI (async) backend + vanilla HTML/JS SPA frontend, PostgreSQL, docker-compose, Alembic migrations, pytest suite, and a single-owner admin panel.

- **Buyers** (in Telegram): browse catalog, cart, checkout via **Bank QRcode** or **Cash on Delivery**, track orders, submit payment proof.
- **Owner/admin**: dashboard with revenue & sales charts, product/category management, order management with status flow, store settings, uploads.

## Stack

| Layer     | Tech |
|-----------|------|
| Backend   | Python 3.12, FastAPI, SQLAlchemy 2 (async), asyncpg |
| DB        | PostgreSQL 15 (migrations via Alembic) |
| Frontend  | Vanilla HTML/CSS/JS SPA (hash router, Telegram WebApp SDK) |
| Infra     | Docker Compose, uvicorn (multi-worker) |
| Tests     | pytest + pytest-asyncio (aiosqlite) |

## Quick start

```bash
cp .env.example .env          # then edit at least SECRET_KEY and ADMIN_TELEGRAM_IDS
docker compose up --build -d
```

On first boot the backend waits for Postgres, runs `alembic upgrade head`, and seeds demo data (store settings, categories, products, and the owner user from `ADMIN_TELEGRAM_IDS[0]`).

- Backend + SPA: http://localhost:8003
- API docs: http://localhost:8003/docs
- Health: http://localhost:8003/api/health

### Demo login (development only)

Outside Telegram, while `APP_ENV=development`, use the demo endpoints:

```bash
# buyer
curl -X POST "http://localhost:8003/api/auth/demo?role=buyer"
# admin (telegram_id from ADMIN_TELEGRAM_IDS[0])
curl -X POST "http://localhost:8003/api/auth/demo?role=admin"
```

Each returns `{ "token": ..., "user": ... }`; pass it as `Authorization: Bearer <token>`.

In Telegram, open the app and the WebApp SDK authenticates automatically via initData (`POST /api/auth/telegram`).

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_ENV` | `production` | `development` enables demo login & dev-only helpers |
| `SECRET_KEY` | — | **Set to a random string** (`openssl rand -hex 32`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | JWT lifetime (7 days) |
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather (validates WebApp initData) |
| `ADMIN_TELEGRAM_IDS` | — | Comma-separated Telegram user IDs with admin role |
| `TELEGRAM_AUTH_MAX_AGE_SECONDS` | `86400` | Max age of a valid Telegram auth payload |
| `POSTGRES_USER/PASSWORD/DB` | `shop/shop/shop` | Database credentials |
| `POSTGRES_PORT` | `5436` | Host port for Postgres |
| `DATABASE_URL` | — | Only for running the backend outside docker-compose |
| `BACKEND_PORT` | `8003` | Host port for the backend/SPA |
| `WORKERS` | `4` | uvicorn worker count |
| `CORS_ORIGINS` | `*` | Allowed browser origins (`*` disables checks) |
| `UPLOAD_DIR` | `/app/uploads` | Upload storage path |
| `MAX_UPLOAD_SIZE_MB` | `5` | Per-file upload limit |
| `STORE_CURRENCY` / `STORE_CURRENCY_SYMBOL` | `USD` / `$` | Defaults used at first boot; editable later in Admin → Settings |

## Payment flows

### Cash on Delivery
`checkout (cod)` → `pending` (unpaid) → admin `confirmed` → `processing` → `shipped` → `delivered` → `completed`

### Bank QRcode
`checkout (bank_qr)` → `pending_payment` (unpaid) → buyer uploads payment proof (`POST /api/orders/{id}/payment-proof`) → `under_review` → admin approves (`confirmed`/`paid`) or `rejected` (restocks + `unpaid`)

Stock is decremented at checkout (transactionally) and restored on buyer cancel or admin reject.

## Admin order status flow

`pending` → confirmed → processing → shipped → delivered → completed
`pending_payment` → under_review → confirmed | rejected
Any cancellable state can be cancelled by buyer (`pending`, `pending_payment`, `confirmed`, `processing`).

## API overview

Public: `GET /api/products`, `GET /api/store`, `GET /api/stores` (buyer store directory), `POST /api/auth/*`
Buyer (auth): `POST /api/auth/*`, `GET|POST|PATCH|DELETE /api/cart`, `POST /api/orders/checkout`, `GET /api/orders`, `GET /api/orders/{id}`, `POST /api/orders/{id}/cancel`, `POST /api/orders/{id}/payment-proof`
Admin (owner): `/api/admin/dashboard`, `/api/admin/products`, `/api/admin/categories`, `/api/admin/orders`, `/api/admin/settings`, `/api/admin/uploads`

Interactive docs at `/docs`.

## Development

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest          # 33 tests
```

Frontend files are plain JS served by the backend (`/`). Validate syntax with `node --check` (the repo has a `frontend/package.json` marking the dir as ESM).

Useful compose commands:

```bash
docker compose down                 # stop
docker compose down -v              # stop + wipe volumes (fresh DB)
docker compose logs -f backend      # tail backend logs
```

## Production notes

- Set a real `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, and `ADMIN_TELEGRAM_IDS`.
- Restrict `CORS_ORIGINS` to your actual origins (or serve the SPA from the same origin — the default setup does).
- Serve behind TLS (Telegram Mini Apps require HTTPS).
- Telegram notification failures are logged and swallowed; they never break an order.
