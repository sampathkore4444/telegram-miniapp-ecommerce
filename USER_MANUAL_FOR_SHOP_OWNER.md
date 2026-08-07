# ShopTrolley — User Manual for Shop Owners

This guide explains how to run your Telegram Mini-App store from the shop owner's side. It covers the admin panel (dashboard, products, orders, coupons, reviews, customers, broadcasts, and settings) plus a short overview of what your buyers see.

> The storefront is a Telegram Mini App: buyers open it inside Telegram and are signed in automatically with their Telegram account. As the owner, you manage everything from the **Admin** section of the same app.

---

## Table of contents

1. [Getting started](#1-getting-started)
2. [Dashboard overview](#2-dashboard-overview)
3. [Products](#3-products)
4. [Categories](#4-categories)
5. [Orders](#5-orders)
6. [Coupons & discounts](#6-coupons--discounts)
7. [Reviews](#7-reviews)
8. [Customers](#8-customers)
9. [Broadcasts](#9-broadcasts)
10. [Store settings](#10-store-settings)
11. [Payments](#11-payments)
12. [Stock alerts & notifications](#12-stock-alerts--notifications)
13. [The buyer's experience](#13-the-buyers-experience)
14. [Frequently asked questions](#14-frequently-asked-questions)

---

## 1. Getting started

### 1.1 How your store gets created

ShopTrolley is a multi-tenant platform. Each store is set up for you after onboarding — see the note below. Once your store exists:

- Buyers find and open your store via its Telegram Mini App link.
- You sign in as the **owner/admin** using your own Telegram account.

### 1.2 Who is the owner?

The owner is a Telegram user whose ID is listed in the platform's `ADMIN_TELEGRAM_IDS` setting (configured by the platform operator, e.g. from the ID you provided on the ShopTrolley signup form). On first boot the system creates this user with the **Admin** role.

Only admins can see the **Admin** menu. Buyers never see it.

### 1.3 Opening the app

1. Open the Telegram Mini App link (starts inside Telegram).
2. Telegram signs you in automatically using your account — no password needed.
3. If the admin menu does not appear, make sure the Telegram ID of the account you are using is registered as an admin.

> **Developer note:** during development (outside Telegram), demo sign-in buttons on the login screen let you try the app as a *Buyer* or as an *Admin*.

### 1.4 Supported languages

Buyers can use the store in **English**, **Bahasa Indonesia**, **Tiếng Việt**, and **Português (BR)**. The language is detected automatically from each buyer's Telegram settings and can be changed in their profile. The admin panel itself is in English.

---

## 2. Dashboard overview

The Dashboard is your home screen in the admin area. It gives you a real-time snapshot of the business.

**Key numbers (KPIs)**
- **Revenue (paid)** — total value of paid orders.
- **Orders** — total number of orders.
- **Pending** — orders waiting for your action.
- **Products** — number of products in your catalog.
- **Low stock (≤5)** — products at or below the low-stock threshold (highlighted in red when there are any).
- **Customers** — number of unique buyers.
- **Average order value** — revenue divided by orders.
- **Repeat customers** — % of customers who ordered more than once.
- **Discounts given** — total value of discounts applied via coupons.

**Charts & reports**
- **Revenue by category** — where your sales come from.
- **Coupon usage** — how many times each coupon was redeemed.
- **Sales — last 14 days** — a daily bar chart plus today's revenue.
- **Orders by status** — counts for each order status.
- **Top products** — best-selling products by quantity sold.
- **Recent orders** — click any row to open that order.

Use the **+ Product** button in the top-right to jump straight to creating a product.

---

## 3. Products

The Products screen is where you manage your catalog. You can search, filter, create, edit, delete, and import/export products.

### 3.1 Filters

- **All / Active / Draft / Archived** — quick status filters.
- **Low stock** — shows only products at or below the low-stock threshold (see [Settings](#10-store-settings)).
- **Search** — type to filter by product name.
- **Load more** — paginates through results (20 per page).

### 3.2 Creating / editing a product

Click **+ New** (or click an existing product to edit). The product editor has these sections:

**Images**
- Add one or more photos with **+ Add image** (up to 5 MB per file).
- Hover a thumbnail and click **×** to remove it.
- The first image is shown as the main photo; extra images become a thumbnail gallery for buyers.

**Details**
- **Name** (required) — shown to buyers.
- **Category** — pick from your categories (see [Categories](#4-categories)).
- **Description** — a free-text description shown on the product page.

**Pricing & stock**
- **Price** (required) — selling price.
- **Compare-at price** (optional) — a higher "original" price; buyers see a strikethrough price and a discount badge (e.g. "-25%").
- **SKU** (optional) — your internal stock-keeping unit.
- **Stock** — quantity available.
- **Status** — `Draft` (hidden), `Active` (shown for sale), or `Archived` (hidden/retired).
- **Feature this product on the home page** — featured products get a "Featured" tag.

**Quantity discount tiers** *(optional)*
- Offer a cheaper per-unit price when a buyer orders a larger quantity, e.g. "5+ → $45.00".
- The tier with the highest `min_quantity` the buyer's quantity reaches wins.
- Variant prices (below) override tier prices.

**Variants** *(optional)*
- Add variants like sizes or colors (e.g. "Red / M").
- Each variant can have its own **stock**, **price** (leave blank to inherit the product price), **options** (e.g. `Color: Red, Size: M`), and an **Active** toggle to hide a variant from buyers.
- Buyers pick a variant on the product page; out-of-stock variants are marked "Sold out" and cannot be ordered.

Click **Save product** when done. Name and price are required.

### 3.3 Statuses explained

| Status    | Meaning                                              |
|-----------|------------------------------------------------------|
| Draft     | Hidden — buyers cannot see it. Use while preparing.  |
| Active    | Visible and available for purchase.                  |
| Archived  | Hidden from the shop; kept in your records.          |

### 3.4 Import / export (CSV)

- **Export CSV** — downloads your full product list as `products_export.csv` (useful for spreadsheets or offline editing).
- **Import CSV** — upload a CSV file to bulk create or update products. The screen reports how many were `created`, `updated`, and `skipped`.

### 3.5 Deleting a product

Use the red **Delete** button on a product row and confirm. **This cannot be undone.**

---

## 4. Categories

Categories organize your catalog and are shown as filter chips on the storefront.

- **+ New** to create a category.
- Each category has a **Name** (required), a **Slug** (used in the URL; auto-generated if left empty), a **Description**, and a **Visible in the shop** toggle.
- A hidden category stays in the admin panel but its products are not shown under it on the storefront.
- **Edit / Delete** buttons appear on each category row. Deleting a category does **not** delete its products — they simply lose that category.

---

## 5. Orders

The Orders screen is your fulfillment center. Every order your buyers place appears here.

### 5.1 Filtering & searching

- **Status pills** — filter by any order status (see the flow below).
- **Search** — find orders by customer name or phone.
- **Load more** — paginates (20 per page).
- **Export CSV** — downloads your orders as `orders_export.csv`.

### 5.2 Order detail

Click any order to open it. You'll see:

- **Customer** — name, Telegram ID, phone, delivery address, and any note the buyer left.
- **Tracking** — enter a **carrier** (e.g. "J&T Express") and **tracking number**, then **Save tracking**. This is shown to the buyer.
- **Items** — products, variants, quantities, and line totals.
- **Totals** — subtotal, delivery fee (or FREE), and total.
- **Payment proof** (for Bank QR orders) — the buyer's uploaded receipt image and transaction reference.
- **History** — a timeline of every status change with timestamps and notes.

### 5.3 Order status flow

Orders move through a fixed sequence. You advance them with the buttons shown in the "Update status" card.

**Cash on Delivery (COD):**

`pending` → `confirmed` → `processing` → `shipped` → `delivered` → `completed`

**Bank QR / Online payments:**

`pending_payment` → `under_review` → `confirmed` (you approve payment) **or** `rejected` (payment not accepted — stock is returned)

**The buttons you will use at each step:**

| Current status | Actions available                              |
|----------------|-------------------------------------------------|
| Pending        | Confirm · Cancel                                |
| Awaiting payment | Confirm · Reject payment · Cancel             |
| Payment under review | Approve payment · Reject payment          |
| Confirmed      | Start processing · Cancel                       |
| Processing     | Mark shipped · Cancel                           |
| Shipped        | Mark delivered                                  |
| Delivered      | Complete order                                  |

> **Important:** Cancelling or rejecting an order **returns the stock** to your inventory automatically. Buyers can cancel on their side only while an order is `pending` or `pending_payment` — after that, only you can cancel.

You can add an optional **internal note** (e.g. "paid via ABA, ref 1234") with each status change; it is recorded in the order history for your reference.

### 5.4 Refunds

In the **Refund** card you can refund part or all of an order amount (up to the order total), optionally with a reason. Confirming a refund:
- Marks the order as `refunded`.
- Records the amount and reason in the order history.
- The buyer sees the refund reflected on their order page.

### 5.5 Tips for smooth fulfillment

- Check the **Pending** count on your Dashboard first thing — those orders need your action.
- Add **tracking** as soon as you ship so buyers can follow their parcel.
- Use the **internal note** field to keep a paper trail for payment references or courier details.

---

## 6. Coupons & discounts

Coupons let you offer discounts that buyers apply at checkout by code.

### 6.1 Creating a coupon

Click **+ New** and fill in:

- **Code** — the text buyers enter (auto-uppercased), e.g. `SAVE10`.
- **Discount type** — `Percent (%)` or `Fixed amount`.
- **Value** — e.g. `10` for 10%, or a fixed amount off (percent cannot exceed 100).
- **Minimum order subtotal** — the order subtotal must reach this value for the coupon to apply (0 = no minimum).
- **Maximum total uses** — leave empty for unlimited.
- **Uses per customer** — how many times one customer can use it.
- **Active from / until** — optional start/end dates and times.
- **Active** — turn the coupon on or off at any time.

### 6.2 Coupon status

Each coupon shows its current status on the list:
- **active** (green) — can be used.
- **expired** — the end date has passed.
- **used up** — all allowed uses are consumed.
- **off** — you switched it off.

The list also shows value, minimum subtotal, usage count (`used/max`), and the validity window.

### 6.3 Where buyers use it

At checkout, buyers enter the code in the **promo code** field. The discount is applied instantly and shown in the order summary. Coupon usage is tracked on your **Dashboard** (Coupon usage) so you can measure which promotions work.

---

## 7. Reviews

Buyers can rate and review products (1–5 stars, optional comment). Reviews only appear on the storefront after you **approve** them.

- Filter by **All / Approved / Hidden**.
- **Approve / Hide** — toggle whether a review is public.
- **Delete** — remove a review permanently.
- Reviews show the rating stars, customer name, comment, and any attached photos.

> **Recommendation:** check Reviews regularly and approve genuine feedback so your catalog builds social proof quickly.

---

## 8. Customers

The Customers screen lists everyone who has ordered from you.

- **Search** — by name, username, or phone.
- **Export CSV** — download your customer list.
- Click a customer for details: order count, total spent, join date, plus a **Manage** card where you can:
  - Add an **internal note** (e.g. "VIP — give priority").
  - **Disable / Enable** the account. Disabling blocks that customer from using the app (e.g. for abuse or fraud).
- The customer's order history is listed below, and each order links back to the full order view.

---

## 9. Broadcasts

Send a one-way message to every active buyer at once, directly in Telegram.

1. Go to **Broadcast**.
2. Type your message (up to 4,000 characters).
3. Click **Send broadcast**.

Notes:
- Only **active** buyers with a Telegram account receive it.
- **Admins are never included**.
- After sending you'll see how many were delivered and how many were skipped.

> Use broadcasts sparingly (new arrivals, flash sales, restock announcements) to avoid annoying your customers.

---

## 10. Store settings

**Settings** is where you configure your store's identity, contact details, delivery, and payment options. Click **Save settings** after any change.

### 10.1 Store

- **Store name** — shown in the header, home page, and footer.
- **Tagline / description** — a short line shown under the store name.
- **Welcome message** — a message shown at the top of the home page.
- **Currency code / symbol** — e.g. `USD` / `$`, or `IDR` / `Rp`. Used everywhere prices are displayed.

### 10.2 Contact

- **Phone**, **Email**, **Address** — shown to buyers (e.g. in order confirmations).

### 10.3 Delivery

- **Delivery fee** — flat fee per order.
- **Free delivery over** — if the cart subtotal reaches this amount, delivery is FREE (leave empty to disable). Buyers see "FREE" at checkout when eligible.

### 10.4 Stock alerts

- **Low-stock alert threshold** — the stock level that triggers admin alerts (default 5). See [Stock alerts & notifications](#12-stock-alerts--notifications).

### 10.5 Payments

- Toggle which payment methods buyers can choose: **Bank QR**, **Cash on Delivery**, and **Online payments**.
- Bank QR details (shown to buyers when they pay):
  - **Bank name**
  - **Account holder name**
  - **Account number**
  - **Payment instructions** — free text, e.g. "Include your order number in the transfer notes".
  - **Bank QR code image** — upload a picture of your bank's payment QR code. Buyers scan it (or are shown it) to pay.

---

## 11. Payments

### 11.1 Payment methods

| Method        | How it works                                                                                                                     |
|---------------|----------------------------------------------------------------------------------------------------------------------------------|
| Bank QR       | Buyer transfers the order total to your bank account using the QR/details you configured, then uploads a receipt/transaction ref. |
| Cash on Delivery (COD) | Buyer pays the courier in cash when the order is delivered.                                                                |
| Online payment | Buyer pays online through the configured payment gateway at checkout.                                                            |

### 11.2 What to do for each

- **Bank QR** — the order lands in `pending_payment`. Once the buyer uploads proof it becomes `under_review`. Open the order, check the **Payment proof** (receipt image + reference), then **Approve payment** (`confirmed`) or **Reject payment** (stock is returned).
- **COD** — the order is `pending`. Confirm, then fulfill through `processing → shipped → delivered → completed`. Collect cash from the courier/customer.
- **Online** — payment is handled by the gateway automatically; orders that are paid arrive ready to fulfill.

> Only enable the payment methods you can actually support. If you have not set up Bank QR details, that option should stay off.

---

## 12. Stock alerts & notifications

### 12.1 Alerts to you (admins)

When your low-stock threshold is configured (Settings → Stock alerts), you receive Telegram notifications on these events:

- ⚠️ **Out of stock** — a product just hit 0.
- ⚠️ **Low stock** — a product dropped to or below the threshold.
- ✅ **Back in stock** — a product was restocked above the threshold.

Alerts fire only when stock *crosses* a boundary, so you won't be spammed on every edit.

### 12.2 Alerts to buyers

If a product is sold out, buyers can tap **Notify me** on the product page. When you restock, they are automatically notified on Telegram with a direct link to the product. This is a great way to win back sales — keep inventory topped up!

---

## 13. The buyer's experience

Understanding the storefront helps you support your customers. Here's what buyers see:

**Home**
- Store name, logo, and welcome message.
- Search box, sort options (newest, popular, price low→high, price high→low).
- Category chips and the product grid, with "recently viewed" items for signed-in buyers.
- **Quick add** (+) on each product card.

**Product page**
- Photo gallery (when multiple images exist), wishlist (♥), and share to Telegram.
- Price, compare-at (strikethrough) price, discount badge, quantity-tier hints.
- Variant selector (size/color), live stock display ("In stock · 30", "Sold out").
- **Add to cart**, **Buy now**, and **Notify me** (when sold out).
- Reviews section with star ratings and the option to write a review.

**Cart & checkout**
- Cart with quantity controls; a badge on the nav shows the item count.
- Checkout collects recipient name, phone, delivery address, and an optional note.
- Saved addresses can be pre-filled with one tap.
- Promo/coupon code field with instant validation.
- Payment method selection (only the methods you enabled appear).
- Checkout reserves stock for the buyer while they pay.

**Order tracking**
- Every order has a timeline of status changes.
- Bank QR orders include the payment details/QR, and buyers upload their receipt + transaction reference from here.
- Buyers can **Cancel** while the order is `pending`/`pending_payment`, **Reorder** previous orders, and **Share** the order via Telegram.

**Profile**
- Their saved addresses, phone, wishlist, and a language switcher.

---

## 14. Frequently asked questions

**Q: Why can't I see the Admin menu?**
Your Telegram account must be registered as an admin. Ask the platform operator to add your Telegram user ID to `ADMIN_TELEGRAM_IDS`, then reopen the app.

**Q: A buyer paid by Bank QR. What do I do?**
Open the order (it will be "Payment under review"), verify the receipt and transaction reference against your bank account, then **Approve payment** (or **Reject** if the payment doesn't match — stock is returned automatically).

**Q: How do I show products to buyers?**
Products must be **Active** to appear in the shop. Draft and archived products are hidden.

**Q: How do I offer free delivery?**
Settings → Delivery → set **Free delivery over** to a subtotal amount. Orders above that get FREE delivery automatically.

**Q: Can I cancel an order?**
Yes — use the **Cancel** button on the order while it's in `pending`, `pending_payment`, `confirmed`, or `processing`. Stock is restored automatically.

**Q: How do I refund a customer?**
Open the order and use the **Refund** card (amount + optional reason). The order is marked `refunded` and the buyer sees the refund on their order page.

**Q: What happens to stock when I edit a product?**
Editing stock adjusts the inventory immediately. If it drops to or below your low-stock threshold, admins are alerted on Telegram.

**Q: Can I bulk-add products?**
Yes — use **Import CSV** on the Products screen. Use **Export CSV** first to see the expected format.

**Q: How do buyers get notified about restocks?**
Buyers tap **Notify me** on sold-out products. When you restock, they're messaged automatically on Telegram.

**Q: How do I announce a sale to everyone?**
Use **Broadcast** to send a Telegram message to all active buyers (you are excluded automatically).

---

*If you need help beyond this guide, contact ShopTrolley support at hello@shoptrolley.com.*
