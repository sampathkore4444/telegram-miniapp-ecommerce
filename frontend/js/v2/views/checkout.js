import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, money, getStore, toast, statusBadge, modal, applyCountBadge } from "../ui.js";

export async function renderCheckout(root) {
  root.innerHTML = "";
  const store = await getStore();
  const cart = await api.get("/api/cart");

  if (cart.items.length === 0) {
    root.appendChild(el(`<div class="container"><div class="empty"><span class="ico">&#128722;</span>Your cart is empty.</div></div>`));
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
  const onlineEnabled = store.online_payments_enabled;
  let method = qrEnabled ? "bank_qr" : codEnabled ? "cod" : onlineEnabled ? "online" : "cod";

  let addresses = [];
  try {
    addresses = (await api.get("/api/addresses")).items || [];
  } catch { /* ignore */ }

  const host = el(`
    <div class="container sticky-page">
      <h1 class="title">Checkout</h1>

      <div class="card section-title">Delivery details</div>
      <div class="card">
        <div class="field"><label>Full name</label><input class="input" id="name" value="${esc(prefillName)}" placeholder="Recipient name" /></div>
        <div class="field"><label>Phone</label><input class="input" id="phone" value="${esc(me.phone || "")}" placeholder="+855 …" /></div>
        <div class="field"><label>Delivery address</label><textarea class="input" id="address" placeholder="Street, building, landmark…">${esc(me.address || "")}</textarea></div>
        <div class="field" style="margin-bottom:0"><label>Note (optional)</label><input class="input" id="note" placeholder="Delivery instructions" /></div>
      </div>

      ${addresses.length ? `
      <div class="card section-title">Saved addresses</div>
      <div class="card">
        <div class="chips" id="addr-chips" style="padding-bottom:0">
          ${addresses.map((a) => `<button class="chip" data-id="${a.id}" title="${esc(a.address)}">${esc(a.label || `${a.recipient_name} · ${a.address.slice(0, 22)}`)}${a.is_default ? " · Default" : ""}</button>`).join("")}
        </div>
      </div>` : ""}

      <div class="card section-title">Payment method</div>
      <div class="card" id="pay-options" style="padding-bottom:6px">
        ${qrEnabled ? `
        <div class="pay-option ${method === "bank_qr" ? "selected" : ""}" data-method="bank_qr">
          <span class="radio"></span>
          <span class="ico">&#128179;</span>
          <div><div class="name">Bank QR</div><div class="desc">Pay by scanning the shop's QR code</div></div>
        </div>` : ""}
        ${onlineEnabled ? `
        <div class="pay-option ${method === "online" ? "selected" : ""}" data-method="online">
          <span class="radio"></span>
          <span class="ico">&#128158;</span>
          <div><div class="name">Online payment</div><div class="desc">Pay instantly with card or wallet</div></div>
        </div>` : ""}
        ${codEnabled ? `
        <div class="pay-option ${method === "cod" ? "selected" : ""}" data-method="cod">
          <span class="radio"></span>
          <span class="ico">&#128176;</span>
          <div><div class="name">Cash on Delivery</div><div class="desc">Pay in cash when your order arrives</div></div>
        </div>` : ""}
      </div>

      <div class="card section-title">Order summary</div>
      <div class="card">
        ${cart.items.map((it) => `
          <div class="row" style="margin-bottom:9px">
            <span class="row-label" style="flex:1;min-width:0">${esc(it.product.name)}${it.variant ? `<span class="small" style="color:var(--accent);font-weight:600"> · ${esc(it.variant.name)}</span>` : ""} × ${it.quantity}</span>
            <span class="row-value">${money(it.unit_price * it.quantity, store)}</span>
          </div>`).join("")}
        <div class="divider"></div>
        <div class="row"><span class="row-label">Subtotal</span><span class="row-value">${money(cart.subtotal, store)}</span></div>
        <div class="row"><span class="row-label">Delivery</span><span class="row-value">${freeEligible ? `<span style="color:var(--green);font-weight:700">FREE</span>` : money(deliveryFee, store)}</span></div>
        <div class="row" id="discount-row" style="display:none"><span class="row-label" style="color:var(--green)">Coupon (<span id="coupon-code">—</span>)</span><span class="row-value" style="color:var(--green);font-weight:700" id="discount-amount">−${money(0, store)}</span></div>
        <div class="divider"></div>
        <div class="row"><span class="row-label">Total</span><span class="total-line" id="total-line">${money(total(), store)}</span></div>
        <div class="divider"></div>
        <div class="coupon-box">
          <input class="input grow" id="coupon" placeholder="Have a promo code? Enter it here" style="text-transform:uppercase" />
          <button class="btn btn-outline" id="coupon-btn">Apply</button>
        </div>
        <p class="small muted" id="coupon-msg" style="margin-top:8px"></p>
      </div>

      <p class="small muted center" style="margin-top:2px">Stock is reserved for ${esc(store.store_name)} once you place the order.</p>

      <div class="sticky-bar">
        <div class="sticky-inner">
          <div>
            <div class="small muted">Total</div>
            <div class="total-line" style="font-size:18px" id="sticky-total">${money(total(), store)}</div>
          </div>
          <button class="btn btn-primary grow" id="place">Place order</button>
        </div>
      </div>
    </div>`);

  const refreshTotals = () => {
    host.querySelector("#total-line").textContent = money(total(), store);
    host.querySelector("#sticky-total").textContent = money(total(), store);
  };
  const applyCouponUI = () => {
    const row = host.querySelector("#discount-row");
    if (couponDiscount > 0) {
      row.style.display = "";
      host.querySelector("#coupon-code").textContent = couponCode;
      host.querySelector("#discount-amount").textContent = `−${money(couponDiscount, store)}`;
    } else {
      row.style.display = "none";
    }
    refreshTotals();
  };

  host.querySelector("#coupon-btn").addEventListener("click", async () => {
    const code = host.querySelector("#coupon").value.trim();
    if (!code) return toast("Enter a promo code", "error");
    const msg = host.querySelector("#coupon-msg");
    const btn = host.querySelector("#coupon-btn");
    btn.disabled = true;
    btn.textContent = "…";
    try {
      const res = await api.post("/api/coupons/check", { code });
      couponCode = res.code;
      couponDiscount = res.discount_amount;
      msg.innerHTML = `<span style="color:var(--green)">${esc(res.message)}</span>`;
      applyCouponUI();
    } catch (err) {
      couponCode = "";
      couponDiscount = 0;
      applyCouponUI();
      msg.textContent = err.message;
    } finally {
      btn.disabled = false;
      btn.textContent = "Apply";
    }
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
      toast("Address filled in", "info", 1500);
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
    if (!payload.recipient_name) return toast("Please enter the recipient name", "error");
    if (!payload.recipient_phone) return toast("Please enter a phone number", "error");
    if (payload.delivery_address.length < 5) return toast("Please enter a delivery address", "error");

    const btn = host.querySelector("#place");
    btn.disabled = true;
    btn.textContent = "Placing order…";
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
      btn.textContent = "Place order";
    }
  });

  root.appendChild(host);

  function renderPayRedirect(order, pay) {
    root.innerHTML = "";
    const success = el(`
      <div class="container">
        <div class="card center" style="padding:28px 16px">
          <div style="width:72px;height:72px;margin:0 auto;border-radius:50%;background:var(--accent-soft);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:34px">&#128179;</div>
          <h1 class="title" style="margin:14px 0 6px">Pay ${money(order.total, store)}</h1>
          <p class="muted">Order <b>${esc(order.order_number)}</b></p>
          <p class="muted small" style="margin-top:8px">You'll be taken to the secure payment page to complete your order.</p>
          <button class="btn btn-primary" id="pay-now" style="margin-top:18px">Pay now</button>
        </div>
        <button class="btn btn-outline" id="later" style="width:100%">View order details</button>
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
            <h1 class="title" style="margin:14px 0 6px">Order placed!</h1>
            <p class="muted">Order <b>${esc(order.order_number)}</b> · ${statusBadge("pending")}</p>
            <p class="muted small" style="margin-top:10px">We'll confirm your order shortly. Total to pay on delivery: <b>${money(order.total, store)}</b>.</p>
            <button class="btn btn-primary" id="view-order" style="margin-top:18px">View order</button>
          </div>
        </div>`);
      success.querySelector("#view-order").addEventListener("click", () => navigate(`order/${order.id}`));
      root.appendChild(success);
    } else {
      const success = el(`
        <div class="container">
          <div class="card center" style="padding:28px 16px">
            <div style="width:72px;height:72px;margin:0 auto;border-radius:50%;background:var(--accent-soft);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:34px">&#128179;</div>
            <h1 class="title" style="margin:14px 0 6px">Pay ${money(order.total, store)}</h1>
            <p class="muted">Order <b>${esc(order.order_number)}</b></p>
            <p class="muted small" style="margin-top:8px">Scan the QR code below and transfer <b>${money(order.total, store)}</b>, then confirm your payment.</p>
          </div>
          <div class="card center">
            ${store.bank_qr_image
              ? `<img class="qr-img" src="${esc(store.bank_qr_image)}" alt="Bank QR" />`
              : `<div class="step-note">The shop hasn't uploaded a QR code yet. Use the bank details below.</div>`}
            <div class="row" style="margin-top:8px"><span class="row-label">Bank</span><span class="row-value">${esc(store.bank_name || "—")}</span></div>
            <div class="row"><span class="row-label">Account name</span><span class="row-value">${esc(store.bank_account_name || "—")}</span></div>
            <div class="row"><span class="row-label">Account no.</span><span class="row-value">${esc(store.bank_account_number || "—")}</span></div>
            <div class="row"><span class="row-label">Amount</span><span class="total-line" style="color:var(--accent)">${money(order.total, store)}</span></div>
            ${store.payment_instructions ? `<p class="small muted" style="margin-top:10px">${esc(store.payment_instructions)}</p>` : ""}
          </div>
          <button class="btn btn-success" id="i-paid">I've made the payment</button>
          <div style="height:8px"></div>
          <button class="btn btn-outline" id="later">View order details</button>
        </div>`);

      success.querySelector("#i-paid").addEventListener("click", () => openProofModal(order));
      success.querySelector("#later").addEventListener("click", () => navigate(`order/${order.id}`));
      root.appendChild(success);
    }
  }

  function openProofModal(order) {
    const host2 = el(`
      <div>
        <p class="muted small" style="margin-bottom:12px">Enter the transaction reference and optionally attach a screenshot of the transfer.</p>
        <div class="field"><label>Transaction reference</label><input class="input" id="ref" placeholder="e.g. BAKONG123456" /></div>
        <div class="field"><label>Receipt screenshot (optional)</label><input class="input" type="file" id="receipt" accept="image/*" /></div>
      </div>`);
    modal({
      title: "Confirm payment",
      body: host2,
      okText: "Submit proof",
      onOk: async () => {
        const ref = host2.querySelector("#ref").value.trim();
        if (ref.length < 3) throw new Error("Enter a valid transaction reference");
        const fd = new FormData();
        fd.append("transaction_ref", ref);
        const file = host2.querySelector("#receipt").files[0];
        if (file) fd.append("receipt", file);
        const updated = await api.upload(`/api/orders/${order.id}/payment-proof`, fd);
        toast("Payment proof submitted", "success");
        navigate(`order/${order.id}`);
      },
    });
  }
}
