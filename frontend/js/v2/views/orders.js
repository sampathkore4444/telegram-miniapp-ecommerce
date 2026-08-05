import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, money, statusBadge, getStore, emptyState, toast, applyCountBadge } from "../ui.js";

const FILTERS = ["", "pending", "pending_payment", "under_review", "processing", "shipped", "delivered", "completed", "cancelled", "rejected", "refunded"];
const FILTER_LABELS = { "": "All", pending: "Pending", pending_payment: "Awaiting payment", under_review: "Payment review", processing: "Processing", shipped: "Shipped", delivered: "Delivered", completed: "Completed", cancelled: "Cancelled", rejected: "Rejected", refunded: "Refunded" };
const STATUS_COLORS = {
  pending: "var(--amber)",
  pending_payment: "var(--amber)",
  under_review: "var(--accent)",
  confirmed: "var(--accent)",
  processing: "var(--accent)",
  shipped: "var(--accent)",
  delivered: "var(--green)",
  completed: "var(--green)",
  cancelled: "var(--red)",
  rejected: "var(--red)",
  refunded: "var(--red)",
};

export async function renderOrders(root) {
  root.innerHTML = "";
  const store = await getStore();
  let status = "";

  const host = el(`
    <div class="container">
      <h1 class="title">My orders</h1>
      <div class="pill-tabs" id="pills"></div>
      <div id="list"></div>
    </div>`);

  const pills = host.querySelector("#pills");
  for (const f of FILTERS) {
    const pill = el(`<button class="pill ${f === status ? "active" : ""}" data-f="${f}">${FILTER_LABELS[f]}</button>`);
    pill.addEventListener("click", () => {
      status = f;
      pills.querySelectorAll(".pill").forEach((p) => p.classList.toggle("active", p === pill));
      load();
    });
    pills.appendChild(pill);
  }

  const list = host.querySelector("#list");
  const load = async () => {
    list.innerHTML = `<div class="skeleton" style="height:120px"></div>`;
    const params = new URLSearchParams({ page: 1, page_size: 20 });
    if (status) params.set("status", status);
    const data = await api.get(`/api/orders?${params}`);
    list.innerHTML = "";

    if (data.items.length === 0) {
      list.appendChild(emptyState("&#128230;", "No orders here yet", "Your placed orders will show up in this list."));
      return;
    }
    for (const o of data.items) {
      const first = o.items[0];
      const img = first?.image_url
        ? `<img src="${esc(first.image_url)}" style="width:54px;height:54px;border-radius:12px;object-fit:cover" onerror="this.remove()">`
        : `<div style="width:54px;height:54px;border-radius:12px;background:var(--bg-soft);display:flex;align-items:center;justify-content:center">&#128230;</div>`;
      const row = el(`
        <div class="card order-card" data-id="${o.id}" style="cursor:pointer;--st:${STATUS_COLORS[o.status] || "var(--border)"};padding:12px">
          <div class="row">
            ${img}
            <div class="grow" style="min-width:0">
              <div class="row">
                <b style="font-size:14px">${esc(o.order_number)}</b>
                ${statusBadge(o.status)}
              </div>
              <div class="small muted" style="margin-top:3px">${o.items.length} item(s) · ${esc(o.payment_method === "cod" ? "Cash on delivery" : o.payment_method === "online" ? "Online payment" : "Bank QR")}</div>
              <div class="row" style="margin-top:6px">
                <span class="total-line" style="font-size:15px">${money(o.total, store)}</span>
                <span class="small muted">${esc(new Date(o.created_at).toLocaleString("en-US", { day: "2-digit", month: "short" }))}</span>
              </div>
              <button class="btn btn-sm btn-outline" data-reorder style="margin-top:8px">↻ Reorder</button>
            </div>
          </div>
        </div>`);
      row.addEventListener("click", () => (window.location.hash = `#/order/${o.id}`));
      row.querySelector("[data-reorder]").addEventListener("click", async (e) => {
        e.stopPropagation();
        try {
          const res = await api.post(`/api/orders/${o.id}/reorder`);
          applyCountBadge(res.cart.item_count);
          toast(`${res.added} item(s) re-added${res.skipped ? ` · ${res.skipped} unavailable` : ""}`, "success");
          navigate("cart");
        } catch (err) {
          toast(err.message, "error");
        }
      });
      list.appendChild(row);
    }
  };

  root.appendChild(host);
  await load();
}
