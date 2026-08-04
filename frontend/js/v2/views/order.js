import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, money, getStore, statusBadge, fmtDate, toast, modal, shareToTelegram, applyCountBadge } from "../ui.js";

export async function renderOrder(root, params) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:200px"></div></div>`;
  const store = await getStore();
  const order = await api.get(`/api/orders/${params.id}`);

  const cancellable = ["pending", "pending_payment"].includes(order.status);
  const canSubmitProof = ["pending_payment", "rejected"].includes(order.status) && order.payment_method === "bank_qr";

  const statusColor = (s) => ({
    pending: "var(--amber)", pending_payment: "var(--amber)", under_review: "var(--accent)",
    confirmed: "var(--accent)", processing: "var(--accent)", shipped: "var(--accent)",
    delivered: "var(--green)", completed: "var(--green)", cancelled: "var(--red)", rejected: "var(--red)", refunded: "var(--red)",
  }[s] || "var(--border)");

  const timeline = order.status_logs.slice().reverse();

  const host = el(`
    <div class="container">
      <div class="card order-card" style="--st:${statusColor(order.status)};padding:14px">
        <div class="row wrap">
          <h1 class="title grow" style="margin-bottom:0">${esc(order.order_number)}</h1>
          <div class="row" style="gap:6px">
            ${statusBadge(order.status)}
            <button class="btn btn-sm btn-outline" id="share" style="padding:6px 10px">Share</button>
          </div>
        </div>
        <p class="small muted" style="margin:6px 0 0">Placed ${fmtDate(order.created_at)} · ${esc(order.payment_method === "cod" ? "Cash on delivery" : "Bank QR payment")}</p>
      </div>

      <div class="card section-title">Status</div>
      <div class="card">
        <ul class="timeline" id="tl"></ul>
      </div>

      <div class="card section-title">Items</div>
      <div class="card">
        ${order.items.map((it) => `
          <div class="row" style="margin-bottom:10px">
            <div style="flex:1;min-width:0">
              <div style="font-weight:600;font-size:14px">${esc(it.product_name)}${it.variant_name ? `<span class="small" style="color:var(--accent);font-weight:600"> · ${esc(it.variant_name)}</span>` : ""}</div>
              <div class="small muted">${money(it.unit_price, store)} × ${it.quantity}</div>
            </div>
            <span class="row-value">${money(it.total, store)}</span>
          </div>`).join("")}
        <div class="divider"></div>
        <div class="row"><span class="row-label">Subtotal</span><span class="row-value">${money(order.subtotal, store)}</span></div>
        <div class="row"><span class="row-label">Delivery</span><span class="row-value">${order.delivery_fee ? money(order.delivery_fee, store) : "FREE"}</span></div>
        ${order.discount > 0 ? `<div class="row"><span class="row-label" style="color:var(--green)">Coupon ${order.coupon_code ? `(${esc(order.coupon_code)})` : ""}</span><span class="row-value" style="color:var(--green);font-weight:700">−${money(order.discount, store)}</span></div>` : ""}
        <div class="divider"></div>
        <div class="row"><span class="row-label">Total</span><span class="total-line">${money(order.total, store)}</span></div>
        ${order.refund_amount != null ? `<div class="row"><span class="row-label" style="color:var(--red)">Refunded</span><span class="row-value" style="color:var(--red);font-weight:700">−${money(order.refund_amount, store)}</span></div>` : ""}
      </div>

      <div class="card section-title">Delivery</div>
      <div class="card">
        <div class="row"><span class="row-label">Recipient</span><span class="row-value">${esc(order.recipient_name)}</span></div>
        <div class="row"><span class="row-label">Phone</span><span class="row-value">${esc(order.recipient_phone)}</span></div>
        <div class="row" style="align-items:flex-start"><span class="row-label">Address</span><span class="row-value" style="text-align:right">${esc(order.delivery_address)}</span></div>
        ${order.delivery_note ? `<div class="row" style="align-items:flex-start"><span class="row-label">Note</span><span class="row-value" style="text-align:right">${esc(order.delivery_note)}</span></div>` : ""}
      </div>

      ${order.payment_method === "bank_qr" ? `
      <div class="card section-title">Payment</div>
      <div class="card">
        ${order.payment_status === "paid"
          ? `<div class="step-note" style="background:var(--green-bg);color:var(--green)">Payment received ${order.paid_at ? fmtDate(order.paid_at) : ""}</div>`
          : order.status === "rejected"
          ? `<div class="step-note" style="background:var(--red-bg);color:var(--red)">Payment was rejected. You can resubmit your proof.</div>`
          : order.status === "under_review"
          ? `<div class="step-note info">Your payment is being verified by the shop.</div>`
          : `<div class="step-note">Payment not yet confirmed.</div>`}
        ${order.receipt_image ? `<div class="small muted" style="margin-bottom:6px">Receipt:</div><img src="${esc(order.receipt_image)}" style="max-width:160px;border-radius:10px;border:1px solid var(--border)" />` : ""}
        ${order.transaction_ref ? `<div class="row" style="margin-top:8px"><span class="row-label">Ref</span><span class="row-value">${esc(order.transaction_ref)}</span></div>` : ""}
      </div>` : ""}

      ${order.cancel_reason ? `<div class="step-note" style="background:var(--red-bg);color:var(--red)">${esc(order.cancel_reason)}</div>` : ""}
      ${order.refund_reason ? `<div class="step-note" style="background:var(--red-bg);color:var(--red)">Refunded (${esc(order.refund_reason)})${order.refunded_at ? ` · ${fmtDate(order.refunded_at)}` : ""}</div>` : ""}

      <div class="btn-row">
        ${canSubmitProof ? `<button class="btn btn-success grow" id="proof">Submit payment proof</button>` : ""}
        ${cancellable ? `<button class="btn btn-danger grow" id="cancel">Cancel order</button>` : ""}
        <button class="btn btn-primary grow" id="reorder">Reorder</button>
      </div>
      <div class="btn-row"><button class="btn btn-outline" id="back">Back to orders</button></div>
    </div>`);

  // Timeline rendering: latest first with done/current markers.
  const tl = host.querySelector("#tl");
  const labels = {
    pending: "Order placed",
    pending_payment: "Awaiting payment",
    under_review: "Payment under review",
    confirmed: "Order confirmed",
    processing: "Processing",
    shipped: "Shipped",
    delivered: "Delivered",
    completed: "Completed",
    cancelled: "Cancelled",
    rejected: "Payment rejected",
    refunded: "Refunded",
  };
  const completedIdx = new Set(["completed", "cancelled", "rejected"]);
  const isDone = completedIdx.has(order.status);
  timeline.forEach((log, i) => {
    const isLast = i === 0;
    const cls = isDone ? "done" : isLast ? "current" : "done";
    const li = el(`
      <li class="${cls}">
        <div class="tl-title">${esc(labels[log.to_status] || log.to_status)}</div>
        <div class="tl-time">${fmtDate(log.created_at)}</div>
        ${log.note ? `<div class="tl-note">${esc(log.note)}</div>` : ""}
      </li>`);
    tl.appendChild(li);
  });

  host.querySelector("#back")?.addEventListener("click", () => navigate("orders"));
  host.querySelector("#reorder")?.addEventListener("click", async () => {
    try {
      const res = await api.post(`/api/orders/${order.id}/reorder`);
      applyCountBadge(res.cart.item_count);
      if (res.skipped) toast(`${res.added} item(s) re-added · ${res.skipped} unavailable`, "success");
      else toast(`${res.added} item(s) re-added to cart`, "success");
      navigate("cart");
    } catch (err) {
      toast(err.message, "error");
    }
  });
  host.querySelector("#share")?.addEventListener("click", () => {
    const bot = store?.telegram_bot_username || "ShopTrolleyBot";
    const link = `https://t.me/${bot}/${bot}?startapp=order_${order.id}`;
    shareToTelegram(`Order ${order.order_number} (${money(order.total, store)}) on ${store.store_name}`, link);
  });
  host.querySelector("#cancel")?.addEventListener("click", async () => {
    modal({
      title: "Cancel order",
      body: `<p class="muted">Are you sure you want to cancel this order?</p>`,
      okText: "Yes, cancel",
      okClass: "btn-danger",
      onOk: async () => {
        await api.post(`/api/orders/${order.id}/cancel`);
        toast("Order cancelled", "success");
        navigate("orders");
      },
    });
  });
  host.querySelector("#proof")?.addEventListener("click", () => {
    const body = el(`
      <div>
        <p class="muted small" style="margin-bottom:10px">You still need to pay <b>${money(order.total, store)}</b>. Enter your transfer reference.</p>
        <div class="field"><label>Transaction reference</label><input class="input" id="ref" placeholder="e.g. BAKONG123456" /></div>
        <div class="field"><label>Receipt screenshot (optional)</label><input class="input" type="file" id="receipt" accept="image/*" /></div>
      </div>`);
    modal({
      title: "Submit payment proof",
      body,
      okText: "Submit",
      onOk: async () => {
        const ref = body.querySelector("#ref").value.trim();
        if (ref.length < 3) throw new Error("Enter a valid transaction reference");
        const fd = new FormData();
        fd.append("transaction_ref", ref);
        const file = body.querySelector("#receipt").files[0];
        if (file) fd.append("receipt", file);
        await api.upload(`/api/orders/${order.id}/payment-proof`, fd);
        toast("Proof submitted", "success");
        navigate(`order/${order.id}`);
      },
    });
  });

  root.innerHTML = "";
  root.appendChild(host);
}
