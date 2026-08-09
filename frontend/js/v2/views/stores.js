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
      <div id="store-list" class="grid-2"></div>
    </div>`);

  const list = host.querySelector("#store-list");
  list.innerHTML = "";
  if (stores.length === 0) {
    list.appendChild(emptyState("&#127983;", "No stores yet", "Come back later."));
  }
  for (const s of stores) {
    const card = el(`
      <div class="store-card" data-slug="${esc(s.slug)}">
        <div class="store-card-body">
          <div class="pname">${esc(s.store_name || s.name)}</div>
          ${s.description ? `<div class="small muted store-desc">${esc(s.description)}</div>` : ""}
          <div class="small muted">${s.product_count} product(s)</div>
        </div>
        <button class="btn btn-outline btn-sm store-visit">Visit store</button>
      </div>`);
    const open = () => {
      setStoreSlug(s.slug);
      navigate("home");
    };
    card.addEventListener("click", open);
    card.querySelector(".store-visit").addEventListener("click", (e) => {
      e.stopPropagation();
      open();
    });
    list.appendChild(card);
  }

  root.innerHTML = "";
  root.appendChild(host);
}
