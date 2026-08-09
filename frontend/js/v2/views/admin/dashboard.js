import { api } from "../../api.js";
import { navigate } from "../../router.js";
import { el, esc, money, getStore, statusBadge, fmtDate } from "../../ui.js";

export async function renderDashboard(root) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:240px"></div></div>`;
  const store = await getStore();
  const data = await api.get("/api/admin/dashboard");

  const analytics = Boolean(store.features?.analytics);
  const coupons = Boolean(store.features?.coupons);

  const max = Math.max(1, ...data.sales_last_14_days.map((d) => d.revenue));
  const bars = data.sales_last_14_days.map((d) => {
    const h = (d.revenue / max) * 100;
    return `<div class="bar-wrap" title="${d.day}: ${money(d.revenue, store)}">
      <div class="bar" style="height:${Math.max(h, 2)}%"></div>
      <span class="bar-lbl">${d.day.slice(8)}</span>
    </div>`;
  }).join("");

  const statusRows = Object.entries(data.orders_by_status || {}).map(([s, c]) => `
    <div class="row" style="margin-bottom:6px"><span class="row-label">${statusBadge(s)}</span><b>${c}</b></div>`).join("");

  const recentRows = data.recent_orders.map((o) => `
    <tr data-id="${o.id}">
      <td class="row-link">${esc(o.order_number)}</td>
      <td>${statusBadge(o.status)}</td>
      <td>${money(o.total, store)}</td>
      <td class="small muted">${fmtDate(o.created_at)}</td>
    </tr>`).join("");

  const host = el(`
    <div class="container">
      <div class="row">
        <h1 class="title grow">Dashboard</h1>
        <div class="btn-row" style="margin:0">
          <button class="btn btn-outline btn-sm" data-nav="admin/stores">Stores</button>
          <button class="btn btn-primary btn-sm" data-nav="admin/products">+ Product</button>
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi"><div class="k-label">Revenue (paid)</div><div class="k-value">${money(data.total_revenue, store)}</div></div>
        <div class="kpi"><div class="k-label">Orders</div><div class="k-value">${data.total_orders}</div></div>
        <div class="kpi"><div class="k-label">Pending</div><div class="k-value">${data.pending_orders}</div></div>
        <div class="kpi"><div class="k-label">Products</div><div class="k-value">${data.products_count}</div></div>
        <div class="kpi"><div class="k-label">Low stock (≤5)</div><div class="k-value" style="${data.low_stock_count ? "color:var(--red)" : ""}">${data.low_stock_count}</div></div>
        <div class="kpi"><div class="k-label">Customers</div><div class="k-value">${data.customers_count}</div></div>
        ${analytics ? `<div class="kpi"><div class="k-label">Avg order value</div><div class="k-value">${money(data.avg_order_value || 0, store)}</div></div>
        <div class="kpi"><div class="k-label">Repeat customers</div><div class="k-value">${data.repeat_customer_rate || 0}%</div></div>` : ""}
        ${coupons ? `<div class="kpi"><div class="k-label">Discounts given</div><div class="k-value">${money(data.total_discount_given || 0, store)}</div></div>` : ""}
      </div>

      ${analytics ? `
      <div class="card section-title">Revenue by category</div>
      <div class="card">
        ${data.revenue_by_category.length === 0 ? '<div class="muted small">No sales yet</div>' : data.revenue_by_category.map((c) => `
          <div class="row" style="margin-bottom:8px">
            <span class="grow" style="font-size:14px;font-weight:600">${esc(c.name)}</span>
            <span class="small muted">${money(c.revenue, store)}</span>
          </div>`).join("")}
      </div>` : ""}

      ${coupons ? `
      <div class="card section-title">Coupon usage</div>
      <div class="card">
        ${data.coupon_redemptions.length === 0 ? '<div class="muted small">No coupons used yet</div>' : data.coupon_redemptions.map((c) => `
          <div class="row" style="margin-bottom:8px">
            <span class="grow" style="font-size:14px;font-weight:600">${esc(c.code)}</span>
            <span class="small muted">${c.redemptions}×</span>
          </div>`).join("")}
      </div>` : ""}

      ${analytics ? `
      <div class="card section-title">Sales · last 14 days</div>
      <div class="card">
        <div class="row" style="margin-bottom:4px"><span class="row-label">Today</span><b>${money(data.today_revenue, store)}</b></div>
        <div class="bar-chart">${bars}</div>
      </div>` : ""}

      <div class="card section-title">Orders by status</div>
      <div class="card">${statusRows || '<div class="muted small">No orders yet</div>'}</div>

      ${analytics ? `
      <div class="card section-title">Top products</div>
      <div class="card">
        ${data.top_products.length === 0 ? '<div class="muted small">No sales yet</div>' : data.top_products.map((p) => `
          <div class="row" style="margin-bottom:8px">
            ${p.image_url ? `<img src="${esc(p.image_url)}" style="width:40px;height:40px;border-radius:8px;object-fit:cover" onerror="this.remove()">` : ""}
            <span class="grow" style="font-size:14px;font-weight:600">${esc(p.name)}</span>
            <span class="small muted">${p.quantity} sold</span>
          </div>`).join("")}
      </div>` : ""}

      <div class="card section-title">Recent orders</div>
      <div class="card" style="padding:6px;overflow-x:auto">
        <table class="table">
          <thead><tr><th>Order</th><th>Status</th><th>Total</th><th>Date</th></tr></thead>
          <tbody>${recentRows || '<tr><td colspan="4" class="muted small">No orders yet</td></tr>'}</tbody>
        </table>
      </div>
    </div>`);

  host.querySelectorAll("tr[data-id]").forEach((tr) => {
    tr.addEventListener("click", () => navigate(`admin/order/${tr.dataset.id}`));
  });
  host.querySelectorAll("[data-nav]").forEach((b) => {
    b.addEventListener("click", () => navigate(b.dataset.nav));
  });

  root.innerHTML = "";
  root.appendChild(host);
}
