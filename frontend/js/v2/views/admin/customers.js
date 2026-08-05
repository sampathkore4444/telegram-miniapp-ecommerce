import { api } from "../../api.js";
import { navigate } from "../../router.js";
import { el, esc, money, getStore, fmtDate, toast, statusBadge } from "../../ui.js";
export async function renderCustomers(root) {
  root.innerHTML = "";
  const store = await getStore();
  let state = { page: 1, pageSize: 20, search: "" };

  const host = el(`
    <div class="container">
      <div class="row">
        <h1 class="title grow">Customers</h1>
        <button class="btn btn-outline btn-sm" id="export">Export CSV</button>
      </div>
      <input class="search" id="search" placeholder="Search by name, username or phone…" />
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
    const data = await api.get(`/api/admin/customers?${params}`);
    if (replace) list.innerHTML = "";

    if (data.items.length === 0) {
      list.appendChild(el(`<div class="empty"><span class="ico">&#128101;</span>No customers found.</div>`));
    }
    for (const c of data.items) {
      const row = el(`
        <div class="card" data-id="${c.id}" style="cursor:pointer">
          <div class="row">
            <div class="grow" style="min-width:0">
              <div class="row">
                <b style="font-size:14px">${esc(c.display_name || "Unknown")}</b>
                ${c.is_active ? "" : `<span class="tag" style="background:var(--red-bg);color:var(--red)">Disabled</span>`}
              </div>
              <div class="small muted" style="margin-top:2px">${c.username ? "@" + esc(c.username) : `TG ${c.telegram_id}`}${c.phone ? ` · ${esc(c.phone)}` : ""}</div>
              <div class="small muted">${c.orders_count} order(s) · spent ${money(c.total_spent, store)}${c.last_order_at ? ` · last ${fmtDate(c.last_order_at)}` : ""}</div>
            </div>
            <span class="menu-chev">›</span>
          </div>
        </div>`);
      row.addEventListener("click", () => navigate(`admin/customer/${c.id}`));
      list.appendChild(row);
    }
    moreBtn.style.display = state.page * state.pageSize < data.total ? "" : "none";
  };

  host.querySelector("#search").addEventListener("input", (e) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => { state.search = e.target.value.trim(); state.page = 1; load(true); }, 300);
  });
  moreBtn.addEventListener("click", () => { state.page += 1; load(false); });
  host.querySelector("#export").addEventListener("click", async () => {
    try {
      await api.download("/api/admin/customers/export", "customers_export.csv");
      toast("Export started", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  root.appendChild(host);
  await load(true);
}

export async function renderCustomerDetail(root, params) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:200px"></div></div>`;
  const store = await getStore();
  const c = await api.get(`/api/admin/customers/${params.id}`);

  const host = el(`
    <div class="container">
      <button class="btn btn-outline btn-sm" id="back" style="margin-bottom:10px">← Back</button>

      <div class="card">
        <div class="row">
          <div class="grow">
            <h1 class="title" style="margin-bottom:2px">${esc(c.display_name || "Unknown")}</h1>
            <p class="small muted">${c.username ? "@" + esc(c.username) + " · " : ""}Telegram ID ${c.telegram_id}</p>
          </div>
          ${c.is_active
            ? `<span class="tag" style="background:var(--green-bg);color:var(--green)">Active</span>`
            : `<span class="tag" style="background:var(--red-bg);color:var(--red)">Disabled</span>`}
        </div>
        <div class="kpi-grid" style="margin-top:12px">
          <div class="kpi"><div class="k-label">Orders</div><div class="k-value">${c.orders_count}</div></div>
          <div class="kpi"><div class="k-label">Total spent</div><div class="k-value">${money(c.total_spent, store)}</div></div>
          <div class="kpi"><div class="k-label">Joined</div><div class="k-value" style="font-size:14px">${c.created_at ? fmtDate(c.created_at) : "—"}</div></div>
        </div>
      </div>

      <div class="card section-title">Manage</div>
      <div class="card">
        <div class="field"><label>Phone</label><input class="input" id="phone" value="${esc(c.phone || "")}" placeholder="—" readonly style="opacity:.7" /></div>
        <div class="field"><label>Note</label><textarea class="input" id="note" placeholder="Internal note about this customer">${esc(c.note || "")}</textarea></div>
        <div class="row" style="gap:8px;flex-wrap:wrap">
          <button class="btn btn-primary" id="save">Save</button>
          <button class="btn ${c.is_active ? "btn-danger" : "btn-success"}" id="toggle">${c.is_active ? "Disable" : "Enable"} account</button>
        </div>
      </div>

      <div class="card section-title">Orders</div>
      <div class="card" style="padding:6px;overflow-x:auto">
        ${c.orders.length === 0
          ? `<div class="muted small" style="padding:10px">No orders yet.</div>`
          : `<table class="table">
              <thead><tr><th>Order</th><th>Status</th><th>Total</th><th>Date</th></tr></thead>
              <tbody>${c.orders.map((o) => `
                <tr data-id="${o.id}">
                  <td class="row-link">${esc(o.order_number)}</td>
                  <td>${statusBadge(o.status)}</td>
                  <td>${money(o.total, store)}</td>
                  <td class="small muted">${fmtDate(o.created_at)}</td>
                </tr>`).join("")}
              </tbody>
            </table>`}
      </div>
    </div>`);

  host.querySelector("#back").addEventListener("click", () => navigate("admin/customers"));
  host.querySelectorAll("tr[data-id]").forEach((tr) => {
    tr.addEventListener("click", () => navigate(`admin/order/${tr.dataset.id}`));
  });

  host.querySelector("#save").addEventListener("click", async () => {
    try {
      await api.patch(`/api/admin/customers/${c.id}`, {
        note: host.querySelector("#note").value.trim() || null,
      });
      toast("Saved", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  host.querySelector("#toggle").addEventListener("click", async () => {
    try {
      await api.patch(`/api/admin/customers/${c.id}`, { is_active: !c.is_active });
      toast(c.is_active ? "Customer disabled" : "Customer enabled", "success");
      renderCustomerDetail(root, params);
    } catch (err) {
      toast(err.message, "error");
    }
  });

  root.innerHTML = "";
  root.appendChild(host);
}
