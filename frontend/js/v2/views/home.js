import { api, getToken } from "../api.js";
import { el, esc, productCard, getStore, emptyState, toast, applyCountBadge } from "../ui.js";
import { t } from "../i18n.js";

let state = { page: 1, pageSize: 12, category: "", search: "", sort: "newest", store: null, total: 0 };

export async function renderHome(root) {
  root.innerHTML = "";
  state = { ...state, page: 1 };
  const store = state.store = await getStore();
  const tagline = store.welcome_message || store.store_description || t("home.welcome");

  const host = el(`
    <div class="container">
      <header class="hero">
        <img class="hero-logo" src="/img/shoptrolley.png?v=2" alt="${esc(store.store_name)}" />
        <h1>${esc(store.store_name)}</h1>
        <p>${esc(tagline)}</p>
      </header>

      <div id="recent" style="display:none"></div>

      <div class="search-wrap">
        <div class="search-field">
          <span class="search-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg></span>
          <input class="search" id="search" placeholder="${esc(t("home.search_placeholder"))}" value="${esc(state.search)}" autocomplete="off" />
          <button class="search-clear hidden" id="search-clear" aria-label="${esc(t("home.clear_search"))}">&#10005;</button>
        </div>
        <div class="sort-bar">
          <div class="sort-box">
            <span class="sort-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 6h16"/><path d="M7 12h10"/><path d="M10 18h4"/></svg></span>
            <select class="sort-select" id="sort" aria-label="${esc(t("home.sort_label"))}">
              <option value="newest">${esc(t("home.sort_newest"))}</option>
              <option value="popular">${esc(t("home.sort_popular"))}</option>
              <option value="price_asc">${esc(t("home.sort_price_asc"))}</option>
              <option value="price_desc">${esc(t("home.sort_price_desc"))}</option>
            </select>
            <span class="sort-chev">&#9662;</span>
          </div>
          <span class="result-count" id="count"></span>
        </div>
      </div>

      <div class="chips" id="cats"></div>
      <div class="grid-2" id="grid"></div>
      <div class="center" style="padding:14px 0">
        <button class="btn btn-outline" id="more" style="display:none">${esc(t("home.load_more"))}</button>
      </div>
      <footer class="page-footer">${esc(store.store_name)} · ${esc(t("home.footer"))}</footer>
    </div>`);

  const grid = host.querySelector("#grid");
  const moreBtn = host.querySelector("#more");
  const countEl = host.querySelector("#count");
  const clearBtn = host.querySelector("#search-clear");
  let debounce = null;

  const toggleClear = () => {
    const hasText = host.querySelector("#search").value.length > 0;
    clearBtn.classList.toggle("hidden", !hasText);
  };

  const addToCart = async (id, btn) => {
    try {
      const cart = await api.post("/api/cart/add", { product_id: id, quantity: 1 });
      applyCountBadge(cart.item_count);
      btn.classList.add("done");
      btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>`;
      toast(t("ui.added_to_cart"), "success", 1500);
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
    chips.appendChild(el(`<button class="chip ${!state.category ? "active" : ""}" data-cat="">${esc(t("home.all"))}</button>`));
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
    countEl.textContent = data.total ? t("home.items_count", { n: data.total }) : "";

    if (replace) grid.innerHTML = "";
    if (data.items.length === 0 && state.page === 1) {
      grid.appendChild(emptyState("&#129300;", t("home.no_products"), t("home.no_products_sub")));
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
    toggleClear();
    debounce = setTimeout(() => {
      state.search = e.target.value.trim();
      state.page = 1;
      loadProducts(true);
    }, 350);
  });

  clearBtn.addEventListener("click", () => {
    const input = host.querySelector("#search");
    input.value = "";
    input.focus();
    toggleClear();
    if (!state.search) return;
    state.search = "";
    state.page = 1;
    loadProducts(true);
  });

  const sortSel = host.querySelector("#sort");
  sortSel.value = state.sort;
  toggleClear();
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

  if (getToken()) {
    try {
      const recent = (await api.get("/api/me/recently-viewed")).items || [];
      const recentEl = host.querySelector("#recent");
      if (recent.length) {
        recentEl.style.display = "";
        recentEl.appendChild(el(`<div style="margin:2px 0 10px"><span style="font-weight:700;font-size:14px;color:var(--text-1)">${esc(t("home.recently_viewed"))}</span></div>`));
        const row = el(`<div class="chips" style="padding:0 0 6px;align-items:stretch"></div>`);
        for (const p of recent) {
          const card = productCard(p, store);
          card.style.flex = "0 0 150px";
          card.style.width = "150px";
          card.addEventListener("click", (e) => {
            if (e.target.closest(".quick-add")) return;
            window.location.hash = `#/product/${p.id}`;
          });
          const qa = card.querySelector(".quick-add");
          if (qa) qa.addEventListener("click", (e) => {
            e.stopPropagation();
            addToCart(p.id, qa);
          });
          row.appendChild(card);
        }
        recentEl.appendChild(row);
      }
    } catch { /* ignore */ }
  }
}
