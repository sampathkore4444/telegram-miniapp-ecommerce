import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, money, getStore, toast, statusBadge, modal, applyCountBadge } from "../ui.js";
import { t } from "../i18n.js";

export async function renderCheckout(root) {
  root.innerHTML = "";
  const store = await getStore();
  const cart = await api.get("/api/cart");

  if (cart.items.length === 0) {
    root.appendChild(el(`<div class="container"><div class="empty"><span class="ico">&#128722;</span>${t("cart.empty_title")}.</div></div>`));
    return;
  }

  const me = await api.get("/api/me");
  const prefillName = `${me.first_name || ""} ${me.last_name || ""}`.trim();
  const freeEligible = store.free_delivery_threshold != null && cart.subtotal >= store.free_delivery_threshold;
  const deliveryFee = freeEligible ? 0 : (store.delivery_fee || 0);

  let couponDiscount = 0;
  let couponCode = "";
  const total = () => cart.subtotal + deliveryFee - couponDiscount;

  const qrEnabled = store.bank_qr_enabled;
  const codEnabled = store.cod_enabled;
  const onlineEnabled = !!store.features?.online_payments && store.online_payments_enabled;
  let method = qrEnabled ? "bank_qr" : codEnabled ? "cod" : onlineEnabled ? "online" : "cod";

  let addresses = [];
  try {
    addresses = (await api.get("/api/addresses")).items || [];
  } catch { /* ignore */ }

  const host = el(`
    <div class="container sticky-page">
      <h1 class="title">${t("checkout.title")}</h1>

      <div class="card section-title">${t("checkout.delivery_details")}</div>
      <div class="card">
        <div class="field"><label>${t("checkout.full_name")}</label><input class="input" id="name" value="${esc(prefillName)}" placeholder="${t("checkout.recipient_ph")}" /></div>
        <div class="field"><label>${t("checkout.phone")}</label><input class="input" id="phone" value="${esc(me.phone || "")}" placeholder="+855 …" /></div>
        <div class="field"><label>${t("checkout.delivery_address")}</label><textarea class="input" id="address" placeholder="${t("checkout.address_ph")}">${esc(me.address || "")}</textarea></div>
        <div class="field" style="margin-bottom:0"><label>${t("checkout.note")}</label><input class="input" id="note" placeholder="${t("checkout.note_ph")}" /></div>
      </div>

      ${addresses.length ? `
      <div class="card section-title">${t("checkout.saved_addresses")}</div>
      <div class="card">
        <div class="chips" id="addr-chips" style="padding-bottom:0">
          ${addresses.map((a) => `<button class="chip" data-id="${a.id}" title="${esc(a.address)}">${esc(a.label || `${a.recipient_name} · ${a.address.slice(0, 22)}`)}${a.is_default ? ` · ${t("profile.default")}` : ""}</button>`).join("")}
        </div>
      </div>` : ""}

      <div class="card section-title">${t("checkout.payment_method")}</div>
      <div class="card" id="pay-options" style="padding-bottom:6px">
        ${qrEnabled ? `
        <div class="pay-option ${method === "bank_qr" ? "selected" : ""}" data-method="bank_qr">
          <span class="radio"></span>
          <span class="ico">&#128179;</span>
          <div><div class="name">${t("checkout.bank_qr")}</div><div class="desc">${t("checkout.bank_qr_desc")}</div></div>
        </div>` : ""}
        ${onlineEnabled ? `
        <div class="pay-option ${method === "online" ? "selected" : ""}" data-method="online">
          <span class="radio"></span>
          <span class="ico">&#128158;</span>
          <div><div class="name">${t("checkout.online")}</div><div class="desc">${t("checkout.online_desc")}</div></div>
        </div>` : ""}
        ${codEnabled ? `
        <div class="pay-option ${method === "cod" ? "selected" : ""}" data-method="cod">
          <span class="radio"></span>
          <span class="ico">&#128176;</span>
          <div><div class="name">${t("checkout.cod")}</div><div class="desc">${t("checkout.cod_desc")}</div></div>
        </div>` : ""}
      </div>

      <div class="card section-title">${t("checkout.order_summary")}</div>
      <div class="card">
        ${cart.items.map((it) => `
          <div class="row" style="margin-bottom:9px">
            <span class="row-label" style="flex:1;min-width:0">${esc(it.product.name)}${it.variant ? `<span class="small" style="color:var(--accent);font-weight:600"> · ${esc(it.variant.name)}</span>` : ""} × ${it.quantity}</span>
            <span class="row-value">${money(it.unit_price * it.quantity, store)}</span>
          </div>`).join("")}
        <div class="divider"></div>
        <div class="row"><span class="row-label">${t("checkout.subtotal")}</span><span class="row-value">${money(cart.subtotal, store)}</span></div>
        <div class="row"><span class="row-label">${t("checkout.delivery")}</span><span class="row-value">${freeEligible ? `<span style="color:var(--green);font-weight:700">${t("checkout.free")}</span>` : money(deliveryFee, store)}</span></div>
        <div class="row" id="discount-row" style="display:none"><span class="row-label" style="color:var(--green)">${t("checkout.coupon")} (<span id="coupon-code">—</span>)</span><span class="row-value" style="color:var(--green);font-weight:700" id="discount-amount">−${money(0, store)}</span></div>
        <div class="divider"></div>
        <div class="row"><span class="row-label">${t("checkout.total")}</span><span class="total-line" id="total-line">${money(total(), store)}</span></div>
        <div class="divider"></div>
        ${store.features?.coupons ? `
        <div class="coupon-box" id="coupon-box">
          <span class="coupon-ico">&#127873;</span>
          <input class="coupon-input" id="coupon" placeholder="${t("checkout.coupon_ph")}" autocapitalize="characters" spellcheck="false" autocomplete="off" aria-label="${t("checkout.promo_code")}" />
          <button class="btn btn-outline" id="coupon-btn">${t("checkout.apply")}</button>
        </div>
        <div class="coupon-applied" id="coupon-applied" style="display:none">
          <span class="coupon-ico">&#127873;</span>
          <span class="coupon-applied-label">${t("checkout.coupon_applied")}</span>
          <span class="coupon-applied-code" id="coupon-applied-code"></span>
          <span class="coupon-applied-amount" id="coupon-applied-amount"></span>
          <button class="coupon-remove" id="coupon-remove" title="${t("checkout.remove_coupon")}" aria-label="${t("checkout.remove_coupon")}">&#10005;</button>
        </div>
        <p class="small coupon-msg" id="coupon-msg" role="status" aria-live="polite" hidden></p>` : ""}
      </div>

      <p class="small muted center" style="margin-top:2px">${t("checkout.stock_reserved", { store: esc(store.store_name) })}</p>

      <div class="sticky-bar">
        <div class="sticky-inner">
          <div>
            <div class="small muted">${t("checkout.total")}</div>
            <div class="total-line" style="font-size:18px" id="sticky-total">${money(total(), store)}</div>
          </div>
          <button class="btn btn-primary grow" id="place">${t("checkout.place_order")}</button>
        </div>
      </div>
    </div>`);

  const refreshTotals = () => {
    host.querySelector("#total-line").textContent = money(total(), store);
    host.querySelector("#sticky-total").textContent = money(total(), store);
  };
  const couponMsg = host.querySelector("#coupon-msg");
  const setMsg = (html, kind) => {
    if (!couponMsg) return;
    couponMsg.className = `small coupon-msg${kind ? ` ${kind}` : ""}`;
    couponMsg.innerHTML = html || "";
    couponMsg.hidden = !html;
  };
  const refreshCouponUI = () => {
    if (!host.querySelector("#coupon-box")) return;
    const applied = couponDiscount > 0;
    host.querySelector("#coupon-box").style.display = applied ? "none" : "";
    host.querySelector("#coupon-applied").style.display = applied ? "" : "none";
    const row = host.querySelector("#discount-row");
    row.style.display = applied ? "" : "none";
    if (applied) {
      host.querySelector("#coupon-applied-code").textContent = couponCode;
      host.querySelector("#coupon-applied-amount").textContent = `−${money(couponDiscount, store)}`;
      host.querySelector("#coupon-code").textContent = couponCode;
      host.querySelector("#discount-amount").textContent = `−${money(couponDiscount, store)}`;
    }
    refreshTotals();
  };
  const applyCoupon = async () => {
    const code = host.querySelector("#coupon").value.trim();
    if (!code) { setMsg(t("checkout.enter_code"), "err"); return; }
    const btn = host.querySelector("#coupon-btn");
    btn.disabled = true;
    btn.textContent = "…";
    try {
      const res = await api.post("/api/coupons/check", { code });
      couponCode = res.code;
      couponDiscount = res.discount_amount;
      setMsg(esc(res.message), "ok");
      refreshCouponUI();
    } catch (err) {
      couponCode = "";
      couponDiscount = 0;
      refreshCouponUI();
      setMsg(esc(err.message), "err");
    } finally {
      btn.disabled = false;
      btn.textContent = t("checkout.apply");
    }
  };
  host.querySelector("#coupon-btn")?.addEventListener("click", applyCoupon);
  host.querySelector("#coupon")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); applyCoupon(); }
  });
  host.querySelector("#coupon-remove")?.addEventListener("click", () => {
    couponCode = "";
    couponDiscount = 0;
    host.querySelector("#coupon").value = "";
    setMsg("", "");
    refreshCouponUI();
    toast(t("checkout.coupon_removed"), "info", 1500);
  });

  host.querySelectorAll(".pay-option").forEach((opt) => {
    opt.addEventListener("click", () => {
      method = opt.dataset.method;
      host.querySelectorAll(".pay-option").forEach((o) => o.classList.toggle("selected", o === opt));
    });
  });

  host.querySelectorAll("#addr-chips .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const a = addresses.find((x) => String(x.id) === chip.dataset.id);
      if (!a) return;
      host.querySelector("#name").value = a.recipient_name;
      host.querySelector("#phone").value = a.recipient_phone;
      host.querySelector("#address").value = a.address;
      toast(t("checkout.address_filled"), "info", 1500);
    });
  });

  host.querySelector("#place").addEventListener("click", async () => {
    const payload = {
      payment_method: method,
      recipient_name: host.querySelector("#name").value.trim(),
      recipient_phone: host.querySelector("#phone").value.trim(),
      delivery_address: host.querySelector("#address").value.trim(),
      delivery_note: host.querySelector("#note").value.trim() || null,
      coupon_code: couponCode || null,
    };
    if (!payload.recipient_name) return toast(t("checkout.need_name"), "error");
    if (!payload.recipient_phone) return toast(t("checkout.need_phone"), "error");
    if (payload.delivery_address.length < 5) return toast(t("checkout.need_address"), "error");

    const btn = host.querySelector("#place");
    btn.disabled = true;
    btn.textContent = t("checkout.placing");
    try {
      const order = await api.post("/api/orders/checkout", payload);
      applyCountBadge(0);
      if (method === "online") {
        const pay = await api.post(`/api/orders/${order.id}/pay`);
        renderPayRedirect(order, pay);
      } else {
        renderSuccess(order);
      }
    } catch (err) {
      toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = t("checkout.place_order");
    }
  });

  root.appendChild(host);

  function renderPayRedirect(order, pay) {
    root.innerHTML = "";
    const success = el(`
      <div class="container">
        <div class="card center" style="padding:28px 16px">
          <div style="width:72px;height:72px;margin:0 auto;border-radius:50%;background:var(--accent-soft);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:34px">&#128179;</div>
          <h1 class="title" style="margin:14px 0 6px">${t("checkout.pay_title", { total: money(order.total, store) })}</h1>
          <p class="muted">${t("checkout.order")} <b>${esc(order.order_number)}</b></p>
          <p class="muted small" style="margin-top:8px">${t("checkout.pay_sub")}</p>
          <button class="btn btn-primary" id="pay-now" style="margin-top:18px">${t("checkout.pay_now")}</button>
        </div>
        <button class="btn btn-outline" id="later" style="width:100%">${t("checkout.view_details")}</button>
      </div>`);
    success.querySelector("#pay-now").addEventListener("click", () => {
      navigate((pay.payment_url || `order/${order.id}`).replace(/^#\/?/, ""));
    });
    success.querySelector("#later").addEventListener("click", () => navigate(`order/${order.id}`));
    root.appendChild(success);
  }

  function renderSuccess(order) {
    root.innerHTML = "";
    if (method === "cod") {
      const success = el(`
        <div class="container">
          <div class="card center" style="padding:34px 16px">
            <div style="width:72px;height:72px;margin:0 auto;border-radius:50%;background:var(--green-bg);color:var(--green);display:flex;align-items:center;justify-content:center;font-size:34px">&#10003;</div>
            <h1 class="title" style="margin:14px 0 6px">${t("checkout.placed")}</h1>
            <p class="muted">${t("checkout.order")} <b>${esc(order.order_number)}</b> · ${statusBadge("pending")}</p>
            <p class="muted small" style="margin-top:10px">${t("checkout.cod_success", { total: money(order.total, store) })}</p>
            <button class="btn btn-primary" id="view-order" style="margin-top:18px">${t("ui.view_order")}</button>
          </div>
        </div>`);
      success.querySelector("#view-order").addEventListener("click", () => navigate(`order/${order.id}`));
      root.appendChild(success);
    } else {
      const success = el(`
        <div class="container">
          <div class="card center" style="padding:28px 16px">
            <div style="width:72px;height:72px;margin:0 auto;border-radius:50%;background:var(--accent-soft);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:34px">&#128179;</div>
            <h1 class="title" style="margin:14px 0 6px">${t("checkout.pay_title", { total: money(order.total, store) })}</h1>
            <p class="muted">${t("checkout.order")} <b>${esc(order.order_number)}</b></p>
            <p class="muted small" style="margin-top:8px">${t("checkout.scan_qr", { total: money(order.total, store) })}</p>
          </div>
          <div class="card center">
            ${store.bank_qr_image
              ? `<img class="qr-img" src="${esc(store.bank_qr_image)}" alt="${t("checkout.bank_qr")}" />`
              : `<div class="step-note">${t("checkout.no_qr")}</div>`}
            <div class="row" style="margin-top:8px"><span class="row-label">${t("checkout.bank")}</span><span class="row-value">${esc(store.bank_name || "—")}</span></div>
            <div class="row"><span class="row-label">${t("checkout.account_name")}</span><span class="row-value">${esc(store.bank_account_name || "—")}</span></div>
            <div class="row"><span class="row-label">${t("checkout.account_no")}</span><span class="row-value">${esc(store.bank_account_number || "—")}</span></div>
            <div class="row"><span class="row-label">${t("checkout.amount")}</span><span class="total-line" style="color:var(--accent)">${money(order.total, store)}</span></div>
            ${store.payment_instructions ? `<p class="small muted" style="margin-top:10px">${esc(store.payment_instructions)}</p>` : ""}
          </div>
          <button class="btn btn-success" id="i-paid">${t("checkout.i_paid")}</button>
          <div style="height:8px"></div>
          <button class="btn btn-outline" id="later">${t("checkout.view_details")}</button>
        </div>`);

      success.querySelector("#i-paid").addEventListener("click", () => openProofModal(order));
      success.querySelector("#later").addEventListener("click", () => navigate(`order/${order.id}`));
      root.appendChild(success);
    }
  }

  function openProofModal(order) {
    const host2 = el(`
      <div>
        <p class="muted small" style="margin-bottom:12px">${t("checkout.proof_sub")}</p>
        <div class="field"><label>${t("checkout.transaction_ref")}</label><input class="input" id="ref" placeholder="e.g. BAKONG123456" /></div>
        <div class="field"><label>${t("checkout.receipt")}</label><input class="input" type="file" id="receipt" accept="image/*" /></div>
      </div>`);
    modal({
      title: t("checkout.confirm_payment"),
      body: host2,
      okText: t("checkout.submit_proof"),
      onOk: async () => {
        const ref = host2.querySelector("#ref").value.trim();
        if (ref.length < 3) throw new Error(t("checkout.invalid_ref"));
        const fd = new FormData();
        fd.append("transaction_ref", ref);
        const file = host2.querySelector("#receipt").files[0];
        if (file) fd.append("receipt", file);
        const updated = await api.upload(`/api/orders/${order.id}/payment-proof`, fd);
        toast(t("checkout.proof_submitted"), "success");
        navigate(`order/${order.id}`);
      },
    });
  }
}
