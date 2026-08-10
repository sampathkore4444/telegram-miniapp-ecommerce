// Hash-based router for the SPA.
import { t } from "./i18n.js";
import { setStoreSlug, getStoreSlug, parseStoreHash } from "./store.js";

const routes = new Map();
let current = null;
let renderFn = null;

export function registerRoute(pattern, handler, { title, titleKey } = {}) {
  routes.set(pattern, { handler, title, titleKey });
}

export function routeTitle(spec) {
  if (spec.titleKey) return t(spec.titleKey);
  return spec.title || "";
}

function parseHash() {
  const hash = window.location.hash;
  const storePart = parseStoreHash(hash);
  let segments;
  if (storePart) {
    setStoreSlug(storePart.slug);
    segments = storePart.rest;
  } else {
    segments = hash
      .replace(/^#\/?/, "")
      .split("/")
      .filter((s) => Boolean(s) && !/^tgWebApp/.test(s));
  }
  return segments.length ? segments : ["home"];
}

function match(segments) {
  for (const [pattern, spec] of routes) {
    const parts = pattern.split("/").filter(Boolean);
    if (parts.length !== segments.length) continue;
    const params = {};
    let ok = true;
    for (let i = 0; i < parts.length; i++) {
      if (parts[i].startsWith(":")) params[parts[i].slice(1)] = decodeURIComponent(segments[i]);
      else if (parts[i] !== segments[i]) { ok = false; break; }
    }
    if (ok) return { name: pattern, params, spec };
  }
  return { name: "notfound", params: {}, spec: routes.get("notfound") };
}

export function navigate(path) {
  window.location.hash = `#/${path.replace(/^#\/?/, "")}`;
}

export function startRouter(root) {
  // Renders are serialized through a promise chain so two overlapping renders
  // (e.g. a store change fires a second hashchange while the first render is
  // still running) can never both append their content to the DOM. Identical
  // renders that are already queued/running are collapsed into one.
  let chain = Promise.resolve();
  let seq = 0;
  let pendingId = null;
  let queuedKey = null;

  const keyForCurrentHash = () => {
    const storePart = parseStoreHash(window.location.hash);
    const slug = storePart ? storePart.slug : getStoreSlug();
    const segments = storePart
      ? storePart.rest
      : window.location.hash
          .replace(/^#\/?/, "")
          .split("/")
          .filter((s) => Boolean(s) && !/^tgWebApp/.test(s));
    return `${slug}|${segments.length ? segments.join("/") : "home"}`;
  };

  const renderOne = async () => {
    const segments = parseHash();
    const { name, params, spec } = match(segments);
    if (!spec) {
      root.innerHTML = `<div class="empty"><span class="ico">&#129300;</span>Page not found</div>`;
      return;
    }
    current = { name, params };
    const rt = routeTitle(spec);
    document.title = rt ? `${rt} · Telegram Shop` : "Telegram Shop";
    root.dataset.route = name;
    await spec.handler(root, params);
    window.scrollTo(0, 0);
    highlightNav();
  };

  const render = (force = false) => {
    const key = keyForCurrentHash();
    const id = ++seq;
    if (!force && pendingId !== null && queuedKey === key) return chain;
    queuedKey = key;
    pendingId = id;
    chain = chain.then(async () => {
      try {
        await renderOne();
      } catch (err) {
        console.error("view error", err);
        root.innerHTML = `<div class="empty"><span class="ico">&#9888;</span><p>Something went wrong.</p><p class="small muted">${err.message}</p></div>`;
      } finally {
        if (pendingId === id) {
          pendingId = null;
          queuedKey = null;
        }
      }
    });
    return chain;
  };

  renderFn = render;
  window.addEventListener("hashchange", () => render());
  render();
}

// Re-render the current view even when the route/store hasn't changed
// (e.g. after a language switch). Bypasses the duplicate-render guard.
export function forceRender() {
  if (renderFn) renderFn(true);
}

export function currentRoute() {
  return current;
}

export function highlightNav() {
  const segments = parseHash();
  const active = segments[0] === "admin" ? "admin" : segments[0];
  document.querySelectorAll(".nav-item").forEach((el) => {
    const isActive =
      el.dataset.nav === active ||
      (active === "product" && el.dataset.nav === "home") ||
      (active === "order" && el.dataset.nav === "orders") ||
      (active === "checkout" && el.dataset.nav === "cart") ||
      (active === "login" && el.dataset.nav === "profile");
    el.classList.toggle("active", isActive);
  });
}
