import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, money, getStore, statusBadge, toast } from "../ui.js";
import { t } from "../i18n.js";

export async function renderPayment(root, params) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:220px"></div></div>`;
  const store = await getStore();

  const [idPart, queryPart] = (params.id || "").split("?");
  const orderId = idPart;
  const tx = new URLSearchParams(queryPart || "").get("tx") || "";

  if (!orderId || !tx) {
    root.innerHTML = `<div class="container"><div class="empty"><span class="ico">&#9888;</span><p>${t("payment.invalid")}</p></div></div>`;
    return;
  }

  let order;
  try {
    order = await api.get(`/api/orders/${orderId}`);
  } catch {
    root.innerHTML = `<div class="container"><div class="empty"><span class="ico">&#9888;</span><p>${t("payment.not_found")}</p></div></div>`;
    return;
  }

  const isPending = order.payment_method === "online" && order.payment_status === "unpaid";
  const isDone = order.payment_status === "paid";

  const host = el(`
    <div class="container">
      <div class="card center" style="padding:30px 16px">
        <div style="width:72px;height:72px;margin:0 auto;border-radius:50%;background:var(--accent-soft);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:34px">&#128179;</div>
        <h1 class="title" style="margin:14px 0 6px">${t("payment.pay", { total: money(order.total, store) })}</h1>
        <p class="muted">${t("payment.order")} <b>${esc(order.order_number)}</b></p>
        <div class="small muted" style="margin-top:6px">${statusBadge(order.status)}</div>
      </div>

      ${isPending ? `
      <div class="card">
        <div class="step-note" style="margin-bottom:10px">${t("payment.sandbox")}</div>
        <button class="btn btn-success grow" id="approve" style="width:100%;margin-bottom:8px">${t("payment.approve")}</button>
        <button class="btn btn-outline grow" id="decline" style="width:100%">${t("payment.decline")}</button>
      </div>` : isDone ? `
      <div class="card center">
        <div class="step-note" style="background:var(--green-bg);color:var(--green)">${t("payment.received")}</div>
        <button class="btn btn-primary grow" id="view" style="width:100%;margin-top:10px">${t("payment.view_order")}</button>
      </div>` : `
      <div class="card center">
        <div class="step-note">${t("payment.was_status", { status: esc(order.payment_status) })}</div>
        <button class="btn btn-primary grow" id="view" style="width:100%;margin-top:10px">${t("payment.view_order")}</button>
      </div>`}
    </div>`);

  host.querySelector("#approve")?.addEventListener("click", async () => {
    await _simulate(true);
  });
  host.querySelector("#decline")?.addEventListener("click", async () => {
    await _simulate(false);
  });
  host.querySelector("#view")?.addEventListener("click", () => navigate(`order/${orderId}`));

  async function _simulate(approved) {
    const btn = host.querySelector(approved ? "#approve" : "#decline");
    btn.disabled = true;
    btn.textContent = approved ? t("payment.processing") : t("payment.declining");
    try {
      await api.post(`/api/orders/${orderId}/pay/simulate`, { provider_ref: tx, approved });
      toast(approved ? t("payment.approved") : t("payment.declined"), approved ? "success" : "info");
      navigate(`order/${orderId}`);
    } catch (err) {
      toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = approved ? t("payment.approve") : t("payment.decline");
    }
  }

  root.innerHTML = "";
  root.appendChild(host);
}
