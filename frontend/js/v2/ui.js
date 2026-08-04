// Shared DOM/UI helpers and store settings cache.
import { api } from "./api.js";

export function el(html) {
  const tpl = document.createElement("template");
  tpl.innerHTML = html.trim();
  return tpl.content.firstElementChild;
}

export function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

let storeCache = null;

export async function getStore(force = false) {
  if (!storeCache || force) {
    storeCache = await api.get("/api/store", false);
  }
  return storeCache;
}

export function money(n, store = storeCache) {
  const symbol = store?.currency_symbol ?? "$";
  const v = Number(n || 0);
  const formatted = v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${symbol}${formatted}`;
}

export function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function toast(message, type = "info", ms = 2600) {
  const wrap = document.getElementById("toast-wrap");
  const t = el(`<div class="toast ${type}">${esc(message)}</div>`);
  wrap.appendChild(t);
  setTimeout(() => t.remove(), ms);
}

export function statusBadge(status) {
  const labels = {
    pending: "Pending",
    pending_payment: "Awaiting payment",
    under_review: "Payment review",
    confirmed: "Confirmed",
    processing: "Processing",
    shipped: "Shipped",
    delivered: "Delivered",
    completed: "Completed",
    cancelled: "Cancelled",
    rejected: "Rejected",
    refunded: "Refunded",
  };
  return `<span class="badge badge-${esc(status)}">${esc(labels[status] || status)}</span>`;
}

export function productCard(p, store) {
  const img = p.images && p.images.length
    ? `<img loading="lazy" src="${esc(p.images[0])}" alt="${esc(p.name)}" onerror="this.style.display='none'">`
    : `<span class="ph">&#128230;</span>`;
  const featured = p.is_featured ? `<span class="tag tag-featured" style="position:absolute;top:8px;right:8px;z-index:2">Featured</span>` : "";
  const onSale = p.compare_at_price && p.compare_at_price > p.price;
  const saleBadge = onSale
    ? `<span class="sale-badge">-${Math.round(((p.compare_at_price - p.price) / p.compare_at_price) * 100)}%</span>`
    : "";
  const compare = p.compare_at_price ? `<span class="compare">${money(p.compare_at_price, store)}</span>` : "";
  const stock = p.in_stock
    ? `<span class="stock-line">${p.stock} in stock</span>`
    : `<span class="stock-line" style="color:var(--red)">Sold out</span>`;
  return el(`
    <div class="product-card" data-id="${p.id}">
      <div class="img-wrap">${saleBadge}${featured}${img}</div>
      <div class="info">
        <div class="pname">${esc(p.name)}</div>
        <div class="price">${money(p.price, store)}${compare}</div>
        ${stock}
      </div>
      ${p.in_stock ? `<button class="quick-add" data-add="${p.id}" aria-label="Add to cart"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg></button>` : ""}
    </div>`);
}

export function emptyState(ico, title, sub = "") {
  return el(`<div class="empty"><span class="ico">${ico}</span><p><b>${esc(title)}</b></p>${sub ? `<p class="small">${esc(sub)}</p>` : ""}</div>`);
}

export function modal({ title, body, onOk, okText = "Confirm", okClass = "btn-primary", okVariant = "primary" }) {
  const root = document.getElementById("modal-root");
  const close = () => root.innerHTML = "";
  const back = el(`
    <div class="modal-backdrop">
      <div class="modal">
        ${title ? `<h3>${esc(title)}</h3>` : ""}
        <div class="modal-body"></div>
        ${onOk ? `
        <div class="btn-row">
          <button class="btn btn-outline grow" data-close>Cancel</button>
          <button class="btn ${okClass} grow" data-ok>${esc(okText)}</button>
        </div>` : ""}
      </div>
    </div>`);
  const bodyEl = back.querySelector(".modal-body");
  bodyEl.appendChild(typeof body === "string" ? el(body) : body);
  back.addEventListener("click", (e) => {
    if (e.target === back) close();
  });
  back.querySelector("[data-close]")?.addEventListener("click", close);
  back.querySelector("[data-ok]")?.addEventListener("click", async () => {
    const btn = back.querySelector("[data-ok]");
    btn.disabled = true;
    try {
      await onOk();
      close();
    } catch (err) {
      toast(err.message, "error");
      btn.disabled = false;
    }
  });
  root.appendChild(back);
}

export function confirmBox(message, title = "Are you sure?") {
  return new Promise((resolve) => {
    modal({
      title,
      body: `<p class="muted">${esc(message)}</p>`,
      okText: "Yes, continue",
      okClass: "btn-danger",
      onOk: async () => resolve(true),
    });
  });
}

export function spinner() {
  return el(`<div class="center" style="padding:40px"><div class="skeleton" style="width:100px;height:14px;margin:8px auto"></div></div>`);
}

// Drag/drop + file upload helper -> returns uploaded URL
export function filePicker({ label = "Upload image", accept = "image/*" } = {}) {
  const host = el(`
    <div>
      <label class="file-drop">
        <input type="file" accept="${accept}" />
        <span class="fd-text">${esc(label)}</span>
      </label>
      <div class="fd-preview" style="margin-top:8px"></div>
    </div>`);
  const input = host.querySelector("input");
  const textEl = host.querySelector(".fd-text");
  const preview = host.querySelector(".fd-preview");
  let resolveFn = null;

  input.addEventListener("change", async () => {
    const file = input.files[0];
    if (!file) return;
    textEl.textContent = "Uploading…";
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await api.upload("/api/admin/uploads?purpose=products", fd);
      textEl.textContent = "Done ✓";
      preview.innerHTML = `<img src="${esc(res.url)}" style="max-width:120px;border-radius:10px;border:1px solid var(--border)">`;
      resolveFn?.(res.url);
      input.disabled = true;
    } catch (err) {
      textEl.textContent = "Upload failed — try again";
      toast(err.message, "error");
    }
  });
  host.pick = () => new Promise((res) => { resolveFn = res; input.click(); });
  host.value = () => preview.querySelector("img")?.src || null;
  return host;
}

export function applyCountBadge(count) {
  const badge = document.getElementById("cart-badge");
  if (!badge) return;
  badge.classList.toggle("hidden", !count);
  badge.textContent = count > 99 ? "99+" : String(count);
}

export function productDeepLink(productId, store) {
  const bot = store?.telegram_bot_username || "ShopTrolleyBot";
  return `https://t.me/${bot}/${bot}?startapp=product_${productId}`;
}

export function shareToTelegram(text, url) {
  const link = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
  try {
    if (window.Telegram?.WebApp?.openTelegramLink) {
      window.Telegram.WebApp.openTelegramLink(link);
    } else {
      window.open(link, "_blank", "noopener");
    }
  } catch {
    window.open(link, "_blank", "noopener");
  }
}

export function starRow(rating, size = 14) {
  const full = "★".repeat(Math.max(0, Math.min(5, Math.round(rating))));
  const empty = "☆".repeat(Math.max(0, 5 - Math.round(rating)));
  return `<span class="stars" style="color:var(--star,#f6b73c);font-size:${size}px;letter-spacing:1px">${full}${empty}</span>`;
}

export function safeVal(selector) {
  return (document.querySelector(selector)?.value || "").trim();
}
