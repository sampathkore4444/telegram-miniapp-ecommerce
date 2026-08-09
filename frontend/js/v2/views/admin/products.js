import { api } from "../../api.js";
import { navigate } from "../../router.js";
import { el, esc, money, getStore, toast, confirmBox, statusBadge } from "../../ui.js";

export async function renderProducts(root) {
  root.innerHTML = "";
  const store = await getStore();
  const STATUS_LABELS = { draft: "Draft", active: "Active", archived: "Archived" };

  let state = { page: 1, pageSize: 20, search: "", status: "", low: false };

  const host = el(`
    <div class="container">
      <div class="row">
        <h1 class="title grow">Products</h1>
        <button class="btn btn-outline btn-sm" id="import">Import CSV</button>
        <button class="btn btn-outline btn-sm" id="export">Export CSV</button>
        <button class="btn btn-primary btn-sm" id="new">+ New</button>
      </div>
      <input type="file" id="csv-file" accept=".csv,text/csv" style="display:none" />
      <input class="search" id="search" placeholder="Search products…" />
      <div class="pill-tabs">
        <button class="pill active" data-s="">All</button>
        <button class="pill" data-s="active">Active</button>
        <button class="pill" data-s="draft">Draft</button>
        <button class="pill" data-s="archived">Archived</button>
        <button class="pill" data-s="low">Low stock</button>
      </div>
      <div id="list"></div>
      <div class="center" style="padding:12px 0"><button class="btn btn-outline" id="more" style="display:none">Load more</button></div>
    </div>`);

  const list = host.querySelector("#list");
  const moreBtn = host.querySelector("#more");
  let debounce = null;

  const load = async (replace = true) => {
    if (replace) list.innerHTML = `<div class="skeleton" style="height:160px"></div>`;
    const params = new URLSearchParams({ page: state.page, page_size: state.pageSize });
    if (state.search) params.set("search", state.search);
    if (state.low) params.set("low_stock", "true");
    else if (state.status) params.set("status", state.status);
    const data = await api.get(`/api/admin/products?${params}`);
    if (replace) list.innerHTML = "";

    if (data.items.length === 0) {
      list.appendChild(el(`<div class="empty"><span class="ico">&#128230;</span>No products found.</div>`));
    }
    for (const p of data.items) {
      const img = p.images && p.images.length ? `<img src="${esc(p.images[0])}" style="width:48px;height:48px;border-radius:8px;object-fit:cover" data-err="remove">` : `<div style="width:48px;height:48px;border-radius:8px;background:var(--bg-soft);display:flex;align-items:center;justify-content:center;color:var(--text-3)">&#128230;</div>`;
      const row = el(`
        <div class="card" data-id="${p.id}" style="cursor:pointer">
          <div class="row">
            ${img}
            <div class="grow" style="min-width:0">
              <div class="row">
                <b style="font-size:14px">${esc(p.name)}</b>
                <span class="badge badge-${esc(p.status)}">${esc(STATUS_LABELS[p.status] || p.status)}</span>
              </div>
              <div class="small muted">${money(p.price, store)} · stock: ${p.stock} · ${p.sold_count} sold</div>
            </div>
            <button class="btn btn-sm btn-danger" data-del style="align-self:flex-start">Delete</button>
          </div>
        </div>`);
      row.addEventListener("click", (e) => {
        if (e.target.closest("[data-del]")) return;
        navigate(`admin/product/${p.id}`);
      });
      row.querySelector("[data-del]").addEventListener("click", async (e) => {
        e.stopPropagation();
        const ok = await confirmBox(`Delete "${p.name}"? This cannot be undone.`, "Delete product");
        if (!ok) return;
        try {
          await api.del(`/api/admin/products/${p.id}`);
          toast("Deleted", "success");
          load(true);
        } catch (err) {
          toast(err.message, "error");
        }
      });
      list.appendChild(row);
    }
    moreBtn.style.display = state.page * state.pageSize < data.total ? "" : "none";
  };

  host.querySelector("#search").addEventListener("input", (e) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => { state.search = e.target.value.trim(); state.page = 1; load(true); }, 300);
  });
  host.querySelectorAll(".pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      state.status = pill.dataset.s;
      state.low = pill.dataset.s === "low";
      state.page = 1;
      host.querySelectorAll(".pill").forEach((p) => p.classList.toggle("active", p === pill));
      load(true);
    });
  });
  host.querySelector("#new").addEventListener("click", () => navigate("admin/product/new"));
  host.querySelector("#export").addEventListener("click", async () => {
    try {
      await api.download("/api/admin/products/export", "products_export.csv");
      toast("Export started", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });
  const fileInput = host.querySelector("#csv-file");
  host.querySelector("#import").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files?.[0];
    fileInput.value = "";
    if (!file) return;
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.upload("/api/admin/products/import", fd);
      toast(`Imported: ${res.created} created, ${res.updated} updated, ${res.skipped} skipped`, "success");
      load(true);
    } catch (err) {
      toast(err.message, "error");
    }
  });
  moreBtn.addEventListener("click", () => { state.page += 1; load(false); });

  root.appendChild(host);
  await load(true);
}
