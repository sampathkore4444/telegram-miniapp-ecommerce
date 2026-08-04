// Hash-based router for the SPA.
const routes = new Map();
let current = null;

export function registerRoute(pattern, handler, { title } = {}) {
  routes.set(pattern, { handler, title });
}

function parseHash() {
  const hash = window.location.hash.replace(/^#\/?/, "");
  const segments = hash
    .split("/")
    .filter((s) => Boolean(s) && !/^tgWebApp/.test(s));
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
  const render = async () => {
    const segments = parseHash();
    const { name, params, spec } = match(segments);
    if (!spec) {
      root.innerHTML = `<div class="empty"><span class="ico">&#129300;</span>Page not found</div>`;
      return;
    }
    current = { name, params };
    document.title = spec.title ? `${spec.title} · Telegram Shop` : "Telegram Shop";
    root.dataset.route = name;
    try {
      await spec.handler(root, params);
    } catch (err) {
      console.error("view error", err);
      root.innerHTML = `<div class="empty"><span class="ico">&#9888;</span><p>Something went wrong.</p><p class="small muted">${err.message}</p></div>`;
    }
    window.scrollTo(0, 0);
    highlightNav();
  };

  window.addEventListener("hashchange", render);
  render();
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
