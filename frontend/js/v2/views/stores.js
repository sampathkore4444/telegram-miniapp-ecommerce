import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, emptyState } from "../ui.js";
import { setStoreSlug } from "../store.js";

export async function renderStoresDirectory(root) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:200px"></div></div>`;
  let stores = [];
  try {
    stores = await api.get("/api/stores", false);
  } catch (err) {
    root.innerHTML = "";
    root.appendChild(emptyState("&#128250;", "Could not load stores", err.message));
    return;
  }

  const host = el(`
    <div class="container">
      <h1 class="title">Browse stores</h1>
      <p class="muted small" style="margin-bottom:12px">Pick a store to start shopping.</p>
      <div id="store-list" class="store-list"></div>
    </div>`);

  const list = host.querySelector("#store-list");
  list.innerHTML = "";
  if (stores.length === 0) {
    list.appendChild(emptyState("&#127983;", "No stores yet", "Come back later."));
  }
  for (const s of stores) {
    const initials = String(s.store_name || s.name || "S").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
    const card = el(`
      <div class="store-card" data-slug="${esc(s.slug)}">
        <div class="store-avatar">${esc(initials)}</div>
        <div class="grow" style="min-width:0">
          <div class="pname">${esc(s.store_name || s.name)}</div>
          ${s.description ? `<div class="small muted store-desc">${esc(s.description)}</div>` : ""}
          <div class="small muted" style="margin-top:2px">${s.product_count} product(s)</div>
        </div>
        <span class="store-chev">&#8250;</span>
      </div>`);
    const open = () => {
      setStoreSlug(s.slug);
      navigate("home");
    };
    card.addEventListener("click", open);
    list.appendChild(card);
  }

  root.innerHTML = "";
  root.appendChild(host);
}
