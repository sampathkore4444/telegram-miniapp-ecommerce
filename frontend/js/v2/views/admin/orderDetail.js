import { api } from "../../api.js";
import { navigate } from "../../router.js";
import { el, esc, money, getStore, statusBadge, fmtDate, toast, confirmBox } from "../../ui.js";

// Mirrors backend ALLOWED_TRANSITIONS.
const NEXT = {
  pending: [["confirmed", "Confirm"], ["cancelled", "Cancel"]],
  pending_payment: [["confirmed", "Confirm"], ["rejected", "Reject payment"], ["cancelled", "Cancel"]],
  under_review: [["confirmed", "Approve payment"], ["rejected", "Reject payment"]],
  confirmed: [["processing", "Start processing"], ["cancelled", "Cancel"]],
  processing: [["shipped", "Mark shipped"], ["cancelled", "Cancel"]],
  shipped: [["delivered", "Mark delivered"]],
  delivered: [["completed", "Complete order"]],
  completed: [],
  cancelled: [],
  rejected: [],
};

const LABELS = {
  pending: "Pending",
  pending_payment: "Awaiting payment",
  under_review: "Payment under review",
  confirmed: "Confirmed",
  processing: "Processing",
  shipped: "Shipped",
  delivered: "Delivered",
  completed: "Completed",
  cancelled: "Cancelled",
  rejected: "Rejected",
  refunded: "Refunded",
};

export async function renderAdminOrderDetail(root, params) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:240px"></div></div>`;
  const store = await getStore();
  const order = await api.get(`/api/admin/orders/${params.id}`);

  const actions = NEXT[order.status] || [];

  const host = el(`
    <div class="container">
      <button class="btn btn-outline btn-sm" id="back" style="margin-bottom:10px">← Back</button>
      <div class="row wrap">
        <h1 class="title grow" style="margin-bottom:0">${esc(order.order_number)}</h1>
        ${statusBadge(order.status)}
      </div>
      <p class="small muted" style="margin:6px 0 12px">${fmtDate(order.created_at)} · ${esc(order.payment_method === "cod" ? "Cash on delivery" : order.payment_method === "online" ? "Online payment" : "Bank QR")} · ${esc(order.payment_status)}</p>

      <div class="card section-title">Customer</div>
      <div class="card">
        <div class="row"><span class="row-label">Name</span><span class="row-value">${esc(order.customer?.display_name || order.recipient_name)}</span></div>
        <div class="row"><span class="row-label">Telegram</span><span class="row-value">${order.customer?.telegram_id ?? "—"}</span></div>
        <div class="row"><span class="row-label">Phone</span><span class="row-value">${esc(order.recipient_phone)}</span></div>
        <div class="row" style="align-items:flex-start"><span class="row-label">Address</span><span class="row-value" style="text-align:right">${esc(order.delivery_address)}</span></div>
        ${order.delivery_note ? `<div class="row" style="align-items:flex-start"><span class="row-label">Note</span><span class="row-value" style="text-align:right">${esc(order.delivery_note)}</span></div>` : ""}
      </div>

      <div class="card section-title">Tracking</div>
      <div class="card">
        <div class="field"><label>Carrier</label><input class="input" id="tcarrier" value="${esc(order.tracking_carrier || "")}" placeholder="e.g. J&T Express" /></div>
        <div class="field"><label>Tracking number</label><input class="input" id="tnum" value="${esc(order.tracking_number || "")}" placeholder="e.g. JTX123456789" /></div>
        <button class="btn btn-primary" id="save-tracking">Save tracking</button>
      </div>

      <div class="card section-title">Items</div>
      <div class="card">
        ${order.items.map((it) => `
          <div class="row" style="margin-bottom:8px">
            <span style="flex:1;min-width:0">${esc(it.product_name)}${it.variant_name ? `<span class="small" style="color:var(--accent);font-weight:600"> · ${esc(it.variant_name)}</span>` : ""} × ${it.quantity}</span>
            <span class="row-value">${money(it.total, store)}</span>
          </div>`).join("")}
        <div class="divider"></div>
        <div class="row"><span class="row-label">Subtotal</span><span class="row-value">${money(order.subtotal, store)}</span></div>
        <div class="row"><span class="row-label">Delivery</span><span class="row-value">${order.delivery_fee ? money(order.delivery_fee, store) : "FREE"}</span></div>
        <div class="divider"></div>
        <div class="row"><span class="row-label">Total</span><span class="total-line">${money(order.total, store)}</span></div>
        ${order.refund_amount != null ? `<div class="row"><span class="row-label" style="color:var(--red)">Refunded</span><span class="row-value" style="color:var(--red);font-weight:700">−${money(order.refund_amount, store)}</span></div>` : ""}
      </div>

      ${order.payment_method === "bank_qr" ? `
      <div class="card section-title">Payment proof</div>
      <div class="card">
        ${order.receipt_image
          ? `<a href="${esc(order.receipt_image)}" target="_blank"><img src="${esc(order.receipt_image)}" style="max-width:200px;border-radius:10px;border:1px solid var(--border)" /></a>`
          : '<div class="muted small">No receipt uploaded.</div>'}
        ${order.transaction_ref ? `<div class="row" style="margin-top:8px"><span class="row-label">Reference</span><span class="row-value">${esc(order.transaction_ref)}</span></div>` : ""}
      </div>` : ""}

      <div class="card section-title">History</div>
      <div class="card">
        <ul class="timeline" style="margin:0">
          ${order.status_logs.slice().reverse().map((l) => `
            <li class="done">
              <div class="tl-title">${esc(LABELS[l.to_status] || l.to_status)}</div>
              <div class="tl-time">${fmtDate(l.created_at)}</div>
              ${l.note ? `<div class="tl-note">${esc(l.note)}</div>` : ""}
            </li>`).join("")}
        </ul>
      </div>

      ${order.cancel_reason ? `<div class="step-note" style="background:var(--red-bg);color:var(--red)">${esc(order.cancel_reason)}</div>` : ""}
      ${order.refund_reason ? `<div class="step-note" style="background:var(--red-bg);color:var(--red)">Refunded (${esc(order.refund_reason)})${order.refunded_at ? ` · ${fmtDate(order.refunded_at)}` : ""}</div>` : ""}

      ${order.refund_amount == null && !["cancelled", "rejected"].includes(order.status) ? `
      <div class="card section-title">Refund</div>
      <div class="card">
        <div class="field"><label>Amount *</label><input class="input" type="number" step="0.01" min="0.01" max="${order.total}" id="refund-amount" value="${order.total}" /></div>
        <div class="field"><label>Reason (optional)</label><input class="input" id="refund-reason" placeholder="e.g. item out of stock" /></div>
        <button class="btn btn-danger" id="refund">Refund order</button>
      </div>` : ""}

      ${actions.length ? `
      <div class="card section-title">Update status</div>
      <div class="card">
        <div class="field"><label>Internal note (optional)</label><input class="input" id="note" placeholder="e.g. paid via ABA, ref …" /></div>
        <div class="btn-row">
          ${actions.map(([status, label], i) => `
            <button class="btn ${i === 0 ? "btn-primary" : "btn-danger"} grow" data-act="${status}">${esc(label)}</button>`).join("")}
        </div>
      </div>` : ""}
    </div>`);

  host.querySelector("#back").addEventListener("click", () => navigate("admin/orders"));
  host.querySelector("#save-tracking")?.addEventListener("click", async () => {
    try {
      await api.patch(`/api/admin/orders/${order.id}/tracking`, {
        tracking_number: host.querySelector("#tnum").value.trim() || null,
        tracking_carrier: host.querySelector("#tcarrier").value.trim() || null,
      });
      toast("Tracking saved", "success");
      renderAdminOrderDetail(root, params);
    } catch (err) {
      toast(err.message, "error");
    }
  });
  host.querySelector("#refund")?.addEventListener("click", async () => {
    const amount = Number(host.querySelector("#refund-amount").value);
    const reason = host.querySelector("#refund-reason").value.trim() || "Refunded by admin";
    if (!(amount > 0)) return toast("Enter a valid refund amount", "error");
    const ok = await confirmBox(`Refund ${money(amount, store)} to the customer? The order will be marked refunded.`, "Confirm refund");
    if (!ok) return;
    try {
      await api.post(`/api/admin/orders/${order.id}/refund`, { amount, reason });
      toast("Order refunded", "success");
      renderAdminOrderDetail(root, params);
    } catch (err) {
      toast(err.message, "error");
    }
  });
  host.querySelectorAll("[data-act]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const to = btn.dataset.act;
      const note = host.querySelector("#note")?.value.trim() || null;
      const isDestructive = ["cancelled", "rejected"].includes(to);
      if (isDestructive) {
        const ok = await confirmBox(`Mark this order as ${to}? Stock will be returned.`, `Confirm ${to}`);
        if (!ok) return;
      }
      try {
        await api.patch(`/api/admin/orders/${order.id}/status`, { status: to, note });
        toast("Status updated", "success");
        renderAdminOrderDetail(root, params);
      } catch (err) {
        toast(err.message, "error");
      }
    });
  });

  root.innerHTML = "";
  root.appendChild(host);
}
