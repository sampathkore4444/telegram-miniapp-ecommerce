import { api } from "../../api.js";
import { navigate } from "../../router.js";
import { el, esc, money, getStore, statusBadge, fmtDate, toast } from "../../ui.js";

const FILTERS = [
  ["", "All"],
  ["under_review", "Payment review"],
  ["pending", "Pending (COD)"],
  ["pending_payment", "Awaiting payment"],
  ["confirmed", "Confirmed"],
  ["processing", "Processing"],
  ["shipped", "Shipped"],
  ["delivered", "Delivered"],
  ["completed", "Completed"],
  ["cancelled", "Cancelled"],
  ["rejected", "Rejected"],
  ["refunded", "Refunded"],
];

export async function renderAdminOrders(root) {
  root.innerHTML = "";
  const store = await getStore();
  let state = { page: 1, pageSize: 20, status: "", search: "" };

  const host = el(`
    <div class="container">
      <div class="row">
        <h1 class="title grow">Orders</h1>
        <button class="btn btn-outline btn-sm" id="export">Export CSV</button>
      </div>
      <input class="search" id="search" placeholder="Search by name or phone…" />
      <div class="pill-tabs" id="pills"></div>
      <div id="list"></div>
      <div class="center" style="padding:12px 0"><button class="btn btn-outline" id="more" style="display:none">Load more</button></div>
    </div>`);

  const pills = host.querySelector("#pills");
  for (const [val, label] of FILTERS) {
    const pill = el(`<button class="pill ${val === state.status ? "active" : ""}" data-f="${val}">${label}</button>`);
    pill.addEventListener("click", () => {
      state.status = val;
      state.page = 1;
      pills.querySelectorAll(".pill").forEach((p) => p.classList.toggle("active", p === pill));
      load(true);
    });
    pills.appendChild(pill);
  }

  const list = host.querySelector("#list");
  const moreBtn = host.querySelector("#more");
  let debounce = null;

  const load = async (replace = true) => {
    if (replace) list.innerHTML = `<div class="skeleton" style="height:160px"></div>`;
    const params = new URLSearchParams({ page: state.page, page_size: state.pageSize });
    if (state.status) params.set("status", state.status);
    if (state.search) params.set("search", state.search);
    const data = await api.get(`/api/admin/orders?${params}`);
    if (replace) list.innerHTML = "";

    if (data.items.length === 0) {
      list.appendChild(el(`<div class="empty"><span class="ico">&#128230;</span>No orders found.</div>`));
    }
    for (const o of data.items) {
      const row = el(`
        <div class="card" data-id="${o.id}" style="cursor:pointer">
          <div class="row">
            <div class="grow" style="min-width:0">
              <div class="row">
                <b style="font-size:14px">${esc(o.order_number)}</b>
                ${statusBadge(o.status)}
              </div>
              <div class="small muted" style="margin-top:2px">
                ${o.customer ? esc(o.customer.display_name) : "Unknown"} · ${esc(o.recipient_phone)}
              </div>
              <div class="small muted">${esc(o.payment_method === "cod" ? "COD" : o.payment_method === "online" ? "Online" : "Bank QR")} · ${fmtDate(o.created_at)}</div>
            </div>
            <b>${money(o.total, store)}</b>
          </div>
        </div>`);
      row.addEventListener("click", () => navigate(`admin/order/${o.id}`));
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
      await api.download("/api/admin/orders/export", "orders_export.csv");
      toast("Export started", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  root.appendChild(host);
  await load(true);
}
