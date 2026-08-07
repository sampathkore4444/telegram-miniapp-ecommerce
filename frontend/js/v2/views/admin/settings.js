import { api } from "../../api.js";
import { el, esc, toast, getStore } from "../../ui.js";

export async function renderSettings(root) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:240px"></div></div>`;
  const store = await getStore();
  const s = await api.get("/api/admin/settings");
  const onlinePay = Boolean(store.features?.online_payments);

  const host = el(`
    <div class="container">
      <h1 class="title">Store settings</h1>

      <div class="card section-title">Store</div>
      <div class="card">
        <div class="field"><label>Store name</label><input class="input" id="name" value="${esc(s.store_name)}" /></div>
        <div class="field"><label>Tagline / description</label><textarea class="input" id="desc">${esc(s.store_description || "")}</textarea></div>
        <div class="field"><label>Welcome message (shown on home)</label><textarea class="input" id="welcome">${esc(s.welcome_message || "")}</textarea></div>
        <div class="row">
          <div class="field grow"><label>Currency code</label><input class="input" id="ccode" value="${esc(s.currency_code)}" /></div>
          <div class="field grow"><label>Symbol</label><input class="input" id="csym" value="${esc(s.currency_symbol)}" /></div>
        </div>
      </div>

      <div class="card section-title">Contact</div>
      <div class="card">
        <div class="field"><label>Phone</label><input class="input" id="cphone" value="${esc(s.contact_phone || "")}" /></div>
        <div class="field"><label>Email</label><input class="input" id="cemail" value="${esc(s.contact_email || "")}" /></div>
        <div class="field"><label>Address</label><textarea class="input" id="caddr">${esc(s.store_address || "")}</textarea></div>
      </div>

      <div class="card section-title">Delivery</div>
      <div class="card">
        <div class="field"><label>Delivery fee</label><input class="input" type="number" step="0.01" min="0" id="dfee" value="${esc(s.delivery_fee)}" /></div>
        <div class="field"><label>Free delivery over (leave empty to disable)</label><input class="input" type="number" step="0.01" min="0" id="dthreshold" value="${s.free_delivery_threshold ?? ""}" /></div>
      </div>

      <div class="card section-title">Stock alerts</div>
      <div class="card">
        <div class="field"><label>Low-stock alert threshold</label><input class="input" type="number" step="1" min="0" max="1000" id="low-stock" value="${s.low_stock_threshold ?? 5}" /></div>
        <p class="small muted" style="margin-top:2px">Admins are notified on Telegram when a product drops to or below this stock level.</p>
      </div>

      <div class="card section-title">Payments</div>
      <div class="card">
        <label class="row" style="cursor:pointer;justify-content:flex-start;gap:10px;margin-bottom:10px">
          <input type="checkbox" id="qr-en" ${s.bank_qr_enabled ? "checked" : ""} />
          <span>Accept <b>Bank QR</b> payments</span>
        </label>
        <label class="row" style="cursor:pointer;justify-content:flex-start;gap:10px;margin-bottom:14px">
          <input type="checkbox" id="cod-en" ${s.cod_enabled ? "checked" : ""} />
          <span>Accept <b>Cash on Delivery</b></span>
        </label>
        <label class="row" style="cursor:pointer;justify-content:flex-start;gap:10px;margin-bottom:14px">
          <input type="checkbox" id="online-en" ${onlinePay && s.online_payments_enabled ? "checked" : ""} ${onlinePay ? "" : "disabled"} />
          <span>Accept <b>Online payments</b>${onlinePay ? "" : `<span class="small muted"> — available on Growth+</span>`}</span>
        </label>
        <div class="field"><label>Bank name</label><input class="input" id="bname" value="${esc(s.bank_name || "")}" /></div>
        <div class="field"><label>Account holder name</label><input class="input" id="bholder" value="${esc(s.bank_account_name || "")}" /></div>
        <div class="field"><label>Account number</label><input class="input" id="bacc" value="${esc(s.bank_account_number || "")}" /></div>
        <div class="field"><label>Payment instructions</label><textarea class="input" id="bins">${esc(s.payment_instructions || "")}</textarea></div>
        <div class="field">
          <label>Bank QR code image</label>
          <div id="qr-slot"></div>
          <input type="file" id="qr-file" accept="image/*" style="display:none" />
          <button class="btn btn-outline btn-sm" id="qr-btn" style="margin-top:8px">${s.bank_qr_image ? "Replace QR" : "Upload QR"}</button>
        </div>
      </div>

      <button class="btn btn-primary" id="save">Save settings</button>
      <div style="height:20px"></div>
    </div>`);

  const qrSlot = host.querySelector("#qr-slot");
  if (s.bank_qr_image) {
    qrSlot.innerHTML = `<img src="${esc(s.bank_qr_image)}" style="max-width:180px;border-radius:12px;border:1px solid var(--border)" />`;
  }
  host.querySelector("#qr-btn").addEventListener("click", () => host.querySelector("#qr-file").click());
  host.querySelector("#qr-file").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await api.upload("/api/admin/uploads?purpose=store", fd);
      qrSlot.innerHTML = `<img src="${esc(res.url)}" style="max-width:180px;border-radius:12px;border:1px solid var(--border)" />`;
      s.bank_qr_image = res.url;
      toast("QR uploaded", "success");
    } catch (err) {
      toast(err.message, "error");
    }
    e.target.value = "";
  });

  host.querySelector("#save").addEventListener("click", async () => {
    const payload = {
      store_name: val("#name"),
      store_description: val("#desc") || null,
      welcome_message: val("#welcome") || null,
      currency_code: val("#ccode"),
      currency_symbol: val("#csym"),
      contact_phone: val("#cphone") || null,
      contact_email: val("#cemail") || null,
      store_address: val("#caddr") || null,
      delivery_fee: Number(val("#dfee") || 0),
      free_delivery_threshold: val("#dthreshold") ? Number(val("#dthreshold")) : null,
      low_stock_threshold: Number(val("#low-stock") || 0),
      bank_qr_enabled: host.querySelector("#qr-en").checked,
      cod_enabled: host.querySelector("#cod-en").checked,
      online_payments_enabled: onlinePay ? host.querySelector("#online-en").checked : false,
      bank_name: val("#bname") || null,
      bank_account_name: val("#bholder") || null,
      bank_account_number: val("#bacc") || null,
      payment_instructions: val("#bins") || null,
      bank_qr_image: s.bank_qr_image || null,
    };
    if (!payload.store_name) return toast("Store name is required", "error");
    try {
      await api.patch("/api/admin/settings", payload);
      toast("Settings saved", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  function val(sel) { return (host.querySelector(sel)?.value || "").trim(); }

  root.innerHTML = "";
  root.appendChild(host);
}
