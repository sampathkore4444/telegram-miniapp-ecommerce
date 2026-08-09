import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, money, getStore, statusBadge, fmtDate, toast, modal, shareToTelegram, applyCountBadge } from "../ui.js";
import { getStoreSlug } from "../store.js";
import { t } from "../i18n.js";

export async function renderOrder(root, params) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:200px"></div></div>`;
  const store = await getStore();
  const order = await api.get(`/api/orders/${params.id}`);

  const cancellable = ["pending", "pending_payment"].includes(order.status);
  const canSubmitProof = ["pending_payment", "rejected"].includes(order.status) && order.payment_method === "bank_qr";
  const payLabel = order.payment_method === "cod"
    ? t("order.pay_cod")
    : order.payment_method === "online"
      ? t("order.pay_online")
      : t("order.pay_bankqr");

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
            <button class="btn btn-sm btn-outline" id="share" style="padding:6px 10px">${t("order.share")}</button>
          </div>
        </div>
        <p class="small muted" style="margin:6px 0 0">${t("order.placed", { date: fmtDate(order.created_at) })} · ${esc(payLabel)}</p>
      </div>

      <div class="card section-title">${t("order.status")}</div>
      <div class="card">
        <ul class="timeline" id="tl"></ul>
      </div>

      <div class="card section-title">${t("order.items")}</div>
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
        <div class="row"><span class="row-label">${t("order.subtotal")}</span><span class="row-value">${money(order.subtotal, store)}</span></div>
        <div class="row"><span class="row-label">${t("order.delivery_fee")}</span><span class="row-value">${order.delivery_fee ? money(order.delivery_fee, store) : t("order.free")}</span></div>
        ${order.discount > 0 ? `<div class="row"><span class="row-label" style="color:var(--green)">${t("order.coupon")} ${order.coupon_code ? `(${esc(order.coupon_code)})` : ""}</span><span class="row-value" style="color:var(--green);font-weight:700">−${money(order.discount, store)}</span></div>` : ""}
        <div class="divider"></div>
        <div class="row"><span class="row-label">${t("order.total")}</span><span class="total-line">${money(order.total, store)}</span></div>
        ${order.refund_amount != null ? `<div class="row"><span class="row-label" style="color:var(--red)">${t("order.refunded")}</span><span class="row-value" style="color:var(--red);font-weight:700">−${money(order.refund_amount, store)}</span></div>` : ""}
      </div>

      <div class="card section-title">${t("order.delivery")}</div>
      <div class="card">
        <div class="row"><span class="row-label">${t("order.recipient")}</span><span class="row-value">${esc(order.recipient_name)}</span></div>
        <div class="row"><span class="row-label">${t("order.phone")}</span><span class="row-value">${esc(order.recipient_phone)}</span></div>
        <div class="row" style="align-items:flex-start"><span class="row-label">${t("order.address")}</span><span class="row-value" style="text-align:right">${esc(order.delivery_address)}</span></div>
        ${order.delivery_note ? `<div class="row" style="align-items:flex-start"><span class="row-label">${t("order.note")}</span><span class="row-value" style="text-align:right">${esc(order.delivery_note)}</span></div>` : ""}
      </div>

      ${order.payment_method === "bank_qr" ? `
      <div class="card section-title">${t("order.payment")}</div>
      <div class="card">
        ${order.payment_status === "paid"
          ? `<div class="step-note" style="background:var(--green-bg);color:var(--green)">${t("order.pay_received", { date: order.paid_at ? fmtDate(order.paid_at) : "" })}</div>`
          : order.status === "rejected"
          ? `<div class="step-note" style="background:var(--red-bg);color:var(--red)">${t("order.pay_rejected")}</div>`
          : order.status === "under_review"
          ? `<div class="step-note info">${t("order.under_review")}</div>`
          : `<div class="step-note">${t("order.not_confirmed")}</div>`}
        ${order.receipt_image ? `<div class="small muted" style="margin-bottom:6px">${t("order.receipt_label")}</div><img src="${esc(order.receipt_image)}" style="max-width:160px;border-radius:10px;border:1px solid var(--border)" />` : ""}
        ${order.transaction_ref ? `<div class="row" style="margin-top:8px"><span class="row-label">${t("order.ref")}</span><span class="row-value">${esc(order.transaction_ref)}</span></div>` : ""}
      </div>` : ""}

      ${order.payment_method === "online" ? `
      <div class="card section-title">${t("order.payment")}</div>
      <div class="card">
        ${order.payment_status === "paid"
          ? `<div class="step-note" style="background:var(--green-bg);color:var(--green)">${t("order.pay_received", { date: order.paid_at ? fmtDate(order.paid_at) : "" })}</div>`
          : order.status === "rejected"
          ? `<div class="step-note" style="background:var(--red-bg);color:var(--red)">${t("order.declined")}</div>`
          : `<div class="step-note">${t("order.not_confirmed")}</div>`}
        ${!order.paid_at ? `<button class="btn btn-primary grow" id="pay-online" style="width:100%;margin-top:10px">${order.status === "rejected" ? t("order.pay_again") : t("order.pay_now")}</button>` : ""}
      </div>` : ""}

      ${order.tracking_number ? `
      <div class="card section-title">${t("order.tracking")}</div>
      <div class="card">
        <div class="row"><span class="row-label">${t("order.carrier")}</span><span class="row-value">${esc(order.tracking_carrier || t("order.courier"))}</span></div>
        <div class="row"><span class="row-label">${t("order.tracking_no")}</span><span class="row-value">${esc(order.tracking_number)}</span></div>
      </div>` : ""}

      ${order.cancel_reason ? `<div class="step-note" style="background:var(--red-bg);color:var(--red)">${esc(order.cancel_reason)}</div>` : ""}
      ${order.refund_reason ? `<div class="step-note" style="background:var(--red-bg);color:var(--red)">${t("order.refund_note", { reason: esc(order.refund_reason), date: order.refunded_at ? ` · ${fmtDate(order.refunded_at)}` : "" })}</div>` : ""}

      <div class="btn-row">
        ${canSubmitProof ? `<button class="btn btn-success grow" id="proof">${t("order.submit_proof")}</button>` : ""}
        ${cancellable ? `<button class="btn btn-danger grow" id="cancel">${t("order.cancel_order")}</button>` : ""}
        <button class="btn btn-primary grow" id="reorder">${t("order.reorder")}</button>
      </div>
      <div class="btn-row"><button class="btn btn-outline" id="back">${t("order.back_to_orders")}</button></div>
    </div>`);

  // Timeline rendering: latest first with done/current markers.
  const tl = host.querySelector("#tl");
  const completedIdx = new Set(["completed", "cancelled", "rejected"]);
  const isDone = completedIdx.has(order.status);
  timeline.forEach((log, i) => {
    const isLast = i === 0;
    const cls = isDone ? "done" : isLast ? "current" : "done";
    const li = el(`
      <li class="${cls}">
        <div class="tl-title">${esc(t("tl." + log.to_status) || log.to_status)}</div>
        <div class="tl-time">${fmtDate(log.created_at)}</div>
        ${log.note ? `<div class="tl-note">${esc(log.note)}</div>` : ""}
      </li>`);
    tl.appendChild(li);
  });

  host.querySelector("#back")?.addEventListener("click", () => navigate("orders"));
  host.querySelector("#pay-online")?.addEventListener("click", async () => {
    try {
      const pay = await api.post(`/api/orders/${order.id}/pay`);
      navigate((pay.payment_url || `order/${order.id}`).replace(/^#\/?/, ""));
    } catch (err) {
      toast(err.message, "error");
    }
  });
  host.querySelector("#reorder")?.addEventListener("click", async () => {
    try {
      const res = await api.post(`/api/orders/${order.id}/reorder`);
      applyCountBadge(res.cart.item_count);
      if (res.skipped) toast(`${t("order.reordered", { n: res.added })} · ${t("order.unavailable", { n: res.skipped })}`, "success");
      else toast(t("order.reordered_cart", { n: res.added }), "success");
      navigate("cart");
    } catch (err) {
      toast(err.message, "error");
    }
  });
  host.querySelector("#share")?.addEventListener("click", () => {
    const bot = store?.telegram_bot_username || "ShopTrolleyBot";
    const slug = store?.store?.slug || getStoreSlug();
    const start = slug ? `store_${slug}_order_${order.id}` : `order_${order.id}`;
    const link = `https://t.me/${bot}/${bot}?startapp=${start}`;
    shareToTelegram(t("order.share_text", { number: order.order_number, total: money(order.total, store), store: store.store_name }), link);
  });
  host.querySelector("#cancel")?.addEventListener("click", async () => {
    modal({
      title: t("order.cancel_title"),
      body: `<p class="muted">${t("order.cancel_body")}</p>`,
      okText: t("order.yes_cancel"),
      okClass: "btn-danger",
      onOk: async () => {
        await api.post(`/api/orders/${order.id}/cancel`);
        toast(t("order.cancelled"), "success");
        navigate("orders");
      },
    });
  });
  host.querySelector("#proof")?.addEventListener("click", () => {
    const body = el(`
      <div>
        <p class="muted small" style="margin-bottom:10px">${t("order.still_pay", { total: money(order.total, store) })}</p>
        <div class="field"><label>${t("order.transaction_ref")}</label><input class="input" id="ref" placeholder="e.g. BAKONG123456" /></div>
        <div class="field"><label>${t("order.receipt_opt")}</label><input class="input" type="file" id="receipt" accept="image/*" /></div>
      </div>`);
    modal({
      title: t("order.submit_proof"),
      body,
      okText: t("order.submit"),
      onOk: async () => {
        const ref = body.querySelector("#ref").value.trim();
        if (ref.length < 3) throw new Error(t("order.invalid_ref"));
        const fd = new FormData();
        fd.append("transaction_ref", ref);
        const file = body.querySelector("#receipt").files[0];
        if (file) fd.append("receipt", file);
        await api.upload(`/api/orders/${order.id}/payment-proof`, fd);
        toast(t("order.proof_submitted"), "success");
        navigate(`order/${order.id}`);
      },
    });
  });

  root.innerHTML = "";
  root.appendChild(host);
}
