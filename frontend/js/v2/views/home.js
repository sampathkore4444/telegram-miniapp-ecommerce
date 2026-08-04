import { api } from "../api.js";
import { el, esc, productCard, getStore, emptyState, toast, applyCountBadge } from "../ui.js";

let state = { page: 1, pageSize: 12, category: "", search: "", sort: "newest", store: null, total: 0 };

export async function renderHome(root) {
  root.innerHTML = "";
  state = { ...state, page: 1 };
  const store = state.store = await getStore();
  const tagline = store.welcome_message || store.store_description || "Welcome to our store!";

  const host = el(`
    <div class="container">
      <header class="hero">
        <div class="hero-logo">&#128722;</div>
        <h1>${esc(store.store_name)}</h1>
        <p>${esc(tagline)}</p>
      </header>

      <div class="search-wrap">
        <span class="search-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg></span>
        <input class="search" id="search" placeholder="Search products…" value="${esc(state.search)}" />
        <select class="sort-select" id="sort" aria-label="Sort products">
          <option value="newest">Newest</option>
          <option value="popular">Most popular</option>
          <option value="price_asc">Price: low to high</option>
          <option value="price_desc">Price: high to low</option>
        </select>
      </div>

      <div class="chips" id="cats"></div>
      <div class="grid-2" id="grid"></div>
      <div class="center" style="padding:14px 0">
        <button class="btn btn-outline" id="more" style="display:none">Load more</button>
      </div>
      <footer class="page-footer">${esc(store.store_name)} · Telegram Mini App</footer>
    </div>`);

  const grid = host.querySelector("#grid");
  const moreBtn = host.querySelector("#more");
  let debounce = null;

  const addToCart = async (id, btn) => {
    try {
      const cart = await api.post("/api/cart/add", { product_id: id, quantity: 1 });
      applyCountBadge(cart.item_count);
      btn.classList.add("done");
      btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>`;
      toast("Added to cart", "success", 1500);
      setTimeout(() => {
        btn.classList.remove("done");
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>`;
      }, 1200);
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const loadCats = async () => {
    const cats = await api.get("/api/categories", false);
    const chips = host.querySelector("#cats");
    chips.appendChild(el(`<button class="chip ${!state.category ? "active" : ""}" data-cat="">All</button>`));
    for (const c of cats) {
      chips.appendChild(el(`<button class="chip ${state.category === c.slug ? "active" : ""}" data-cat="${esc(c.slug)}">${esc(c.name)}</button>`));
    }
    chips.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        state.category = chip.dataset.cat;
        state.page = 1;
        chips.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === chip));
        loadProducts(true);
      });
    });
  };

  const loadProducts = async (replace) => {
    if (replace) grid.innerHTML = "";
    if (state.page === 1 && !replace) grid.innerHTML = `<div class="skeleton" style="height:200px"></div>`;
    const params = new URLSearchParams({ page: state.page, page_size: state.pageSize, sort: state.sort });
    if (state.category) params.set("category", state.category);
    if (state.search) params.set("search", state.search);
    const data = await api.get(`/api/products?${params}`, false);
    state.total = data.total;

    if (replace) grid.innerHTML = "";
    if (data.items.length === 0 && state.page === 1) {
      grid.appendChild(emptyState("&#129300;", "No products found", "Try a different search or category."));
    } else {
      for (const p of data.items) {
        const card = productCard(p, store);
        card.addEventListener("click", (e) => {
          if (e.target.closest(".quick-add")) return;
          window.location.hash = `#/product/${p.id}`;
        });
        const qa = card.querySelector(".quick-add");
        if (qa) qa.addEventListener("click", (e) => {
          e.stopPropagation();
          addToCart(p.id, qa);
        });
        grid.appendChild(card);
      }
    }
    const hasMore = state.page * state.pageSize < data.total;
    moreBtn.style.display = hasMore ? "" : "none";
  };

  host.querySelector("#search").addEventListener("input", (e) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      state.search = e.target.value.trim();
      state.page = 1;
      loadProducts(true);
    }, 350);
  });

  const sortSel = host.querySelector("#sort");
  sortSel.value = state.sort;
  sortSel.addEventListener("change", () => {
    state.sort = sortSel.value;
    state.page = 1;
    loadProducts(true);
  });

  moreBtn.addEventListener("click", () => {
    state.page += 1;
    loadProducts(false);
  });

  root.appendChild(host);
  loadCats();
  await loadProducts(true);
}
