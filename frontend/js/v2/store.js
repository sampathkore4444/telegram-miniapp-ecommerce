// Store context: resolves the active store slug from the URL hash
// (#/s/:slug/...) or a Telegram start_param (store_<slug>), persists it,
// and exposes it so api.js can attach the X-Store-Slug header.
export const STORE_KEY = "tgshop_store_slug";

export function getStoreSlug() {
  return localStorage.getItem(STORE_KEY) || "";
}

export function setStoreSlug(slug) {
  const clean = String(slug || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (clean === getStoreSlug()) return;
  if (clean) localStorage.setItem(STORE_KEY, clean);
  else localStorage.removeItem(STORE_KEY);
  window.dispatchEvent(new Event("storechange"));
}

export function clearStoreSlug() {
  setStoreSlug("");
}

// Parse "#/s/:slug/rest" -> { slug, rest: ["rest"] } or null when the hash
// does not carry a store prefix. tgWebApp crumbs are skipped like the router does.
export function parseStoreHash(hash) {
  const clean = String(hash || "")
    .replace(/^#\/?/, "")
    .split("/")
    .filter((s) => Boolean(s) && !/^tgWebApp/.test(s));
  if (clean[0] === "s" && clean[1]) {
    return { slug: clean[1], rest: clean.slice(2) };
  }
  return null;
}

// Telegram start_param (e.g. "store_my-shop") -> store slug, "" if none.
export function storeSlugFromStartParam(initData) {
  if (!initData) return "";
  try {
    const start = (new URLSearchParams(initData).get("start_param") || "").trim();
    const m = start.match(/^store_([a-z0-9-]+)/);
    return m ? m[1] : "";
  } catch {
    return "";
  }
}

// Telegram start_param -> hash route, "" if none. Handles store-scoped
// deep links so shared product/order links land on the right store.
// Supported: "store_<slug>", "product_<id>", "order_<id>", and the
// store-scoped forms "store_<slug>_product_<id>" / "store_<slug>_order_<id>".
export function startParamRoute(initData) {
  if (!initData) return "";
  try {
    const start = (new URLSearchParams(initData).get("start_param") || "").trim();
    let m = start.match(/^store_([a-z0-9-]+)_(product|order)_(\d+)$/);
    if (m) return `s/${m[1]}/${m[2]}/${m[3]}`;
    m = start.match(/^store_([a-z0-9-]+)$/);
    if (m) return `s/${m[1]}`;
    m = start.match(/^(product|order)_(\d+)$/);
    if (m) return `${m[1]}/${m[2]}`;
    return "";
  } catch {
    return "";
  }
}

// Shareable deep link to a store's home, e.g. #/s/my-shop.
export function storeHomeHash(slug) {
  return slug ? `#/s/${encodeURIComponent(slug)}` : "#/home";
}
