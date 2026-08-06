import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, getStore, toast, confirmBox } from "../ui.js";
import { logout } from "../auth.js";
import { attachGeoButton } from "../geo.js";
import { t, getLang, LANGS, LANG_META, setLang } from "../i18n.js";

export async function renderProfile(root) {
  root.innerHTML = "";
  const store = await getStore();
  const me = await api.get("/api/me");

  const initials = (me.first_name?.[0] || "") + (me.last_name?.[0] || "") || "U";
  const host = el(`
    <div class="container">
      <div class="profile-hero">
        <div class="avatar">${me.photo_url ? `<img src="${esc(me.photo_url)}" />` : esc(initials)}</div>
        <h1>${esc(me.display_name || me.first_name || t("profile.user"))}</h1>
        <p>${me.username ? "@" + esc(me.username) : t("profile.telegram_id", { id: me.telegram_id })}</p>
        ${me.role === "admin" ? `<div style="position:relative;z-index:1;margin-top:8px"><span class="tag" style="background:rgba(255,255,255,0.2);color:#fff">${t("profile.store_owner")}</span></div>` : ""}
      </div>

      <div class="card section-title">${t("profile.contact_details")}</div>
      <div class="card">
        <div class="field"><label>${t("profile.phone")}</label><input class="input" id="phone" value="${esc(me.phone || "")}" placeholder="+855 …" /></div>
        <div class="field">
          <div class="row" style="justify-content:space-between;align-items:center;margin-bottom:6px">
            <label style="margin:0">${t("profile.default_address")}</label>
            <button class="btn btn-sm btn-outline" id="geo-btn" type="button">&#128205; ${t("profile.use_location")}</button>
          </div>
          <textarea class="input" id="address" placeholder="${t("profile.address_ph")}">${esc(me.address || "")}</textarea>
          <p class="small geo-status" id="geo-status" hidden></p>
        </div>
        <button class="btn btn-primary" id="save">${t("profile.save_details")}</button>
      </div>

      <div class="card section-title">${t("profile.saved_addresses")}</div>
      <div class="card">
        <div id="addr-list"></div>
        <button class="btn btn-outline btn-sm" id="addr-add" style="margin-top:8px">${t("profile.add_address")}</button>
      </div>

      ${me.role !== "admin" ? `
      <div class="card section-title">${t("profile.my_account")}</div>
      <div class="card" style="padding:4px 14px">
        <button class="menu-item" data-nav="orders"><span class="menu-ico">&#128203;</span>${t("profile.my_orders")}<span class="menu-chev">›</span></button>
        <button class="menu-item" data-nav="wishlist"><span class="menu-ico">&#10084;&#65039;</span>${t("profile.wishlist")}<span class="menu-chev">›</span></button>
      </div>` : ""}

      ${me.role === "admin" ? `
      <div class="card section-title">${t("profile.store_management")}</div>
      <div class="card" style="padding:4px 14px">
        <button class="menu-item" data-admin="admin"><span class="menu-ico">&#128200;</span>${t("profile.dashboard")}<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/products"><span class="menu-ico">&#128230;</span>${t("profile.products")}<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/orders"><span class="menu-ico">&#128203;</span>${t("profile.orders")}<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/customers"><span class="menu-ico">&#128101;</span>${t("profile.customers")}<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/categories"><span class="menu-ico">&#128193;</span>${t("profile.categories")}<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/coupons"><span class="menu-ico">&#127991;</span>${t("profile.coupons")}<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/reviews"><span class="menu-ico">&#11088;</span>${t("profile.reviews")}<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/broadcasts"><span class="menu-ico">&#128227;</span>${t("profile.broadcasts")}<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/settings"><span class="menu-ico">&#9881;</span>${t("profile.settings")}<span class="menu-chev">›</span></button>
      </div>` : ""}

      <div class="card section-title">${t("profile.language")}</div>
      <div class="card">
        <select class="select" id="lang-select" aria-label="${t("profile.language")}">
          ${LANGS.map((l) => `<option value="${l}" ${getLang() === l ? "selected" : ""}>${LANG_META[l].flag} ${LANG_META[l].label}</option>`).join("")}
        </select>
      </div>

      <button class="btn btn-danger" id="logout" style="margin-top:14px">${t("profile.log_out")}</button>
      <footer class="page-footer">${esc(store.store_name)}</footer>
    </div>`);

  host.querySelector("#save").addEventListener("click", async () => {
    try {
      await api.patch("/api/me", {
        phone: host.querySelector("#phone").value.trim() || null,
        address: host.querySelector("#address").value.trim() || null,
      });
      toast(t("profile.saved"), "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  host.querySelector("#lang-select").addEventListener("change", (e) => setLang(e.target.value));

  attachGeoButton(
    host.querySelector("#geo-btn"),
    host.querySelector("#geo-status"),
    host.querySelector("#address")
  );

  const addrList = host.querySelector("#addr-list");

  const renderAddrList = async () => {
    let items;
    try {
      items = (await api.get("/api/addresses")).items || [];
    } catch (err) {
      return toast(err.message, "error");
    }
    addrList.innerHTML = "";
    if (items.length === 0) {
      addrList.appendChild(el(`<p class="muted small">${t("profile.no_addresses")}</p>`));
    }
    for (const a of items) {
      const row = el(`
        <div style="padding:10px 0;border-bottom:1px solid var(--border)">
          <div class="row">
            <div class="grow" style="min-width:0">
              <div class="row">
                <b style="font-size:13px">${esc(a.label || t("profile.address"))}</b>
                ${a.is_default ? `<span class="tag" style="background:var(--green-bg);color:var(--green)">${t("profile.default")}</span>` : ""}
              </div>
              <div class="small muted" style="margin-top:2px">${esc(a.recipient_name)} · ${esc(a.recipient_phone)}</div>
              <div class="small muted">${esc(a.address)}</div>
            </div>
          </div>
          <div class="btn-row" style="margin-top:8px">
            ${a.is_default ? "" : `<button class="btn btn-sm btn-outline" data-set="${a.id}">${t("profile.set_default")}</button>`}
            <button class="btn btn-sm btn-outline" data-edit="${a.id}">${t("profile.edit")}</button>
            <button class="btn btn-sm btn-danger" data-del="${a.id}">${t("profile.delete")}</button>
          </div>
        </div>`);
      row.querySelector("[data-set]")?.addEventListener("click", async () => {
        try {
          await api.patch(`/api/addresses/${a.id}`, { is_default: true });
          toast(t("profile.default_set"), "success");
          renderAddrList();
        } catch (err) {
          toast(err.message, "error");
        }
      });
      row.querySelector("[data-edit]")?.addEventListener("click", () => renderAddrForm(a));
      row.querySelector("[data-del]")?.addEventListener("click", async () => {
        const ok = await confirmBox(t("profile.delete_confirm"), t("profile.delete_title"));
        if (!ok) return;
        try {
          await api.del(`/api/addresses/${a.id}`);
          toast(t("profile.deleted"), "success");
          renderAddrList();
        } catch (err) {
          toast(err.message, "error");
        }
      });
      addrList.appendChild(row);
    }
  };

  const renderAddrForm = (addr) => {
    addrList.innerHTML = "";
    const form = el(`
      <div>
        <div class="field"><label>${t("profile.label_field")}</label><input class="input" id="alabel" value="${esc(addr?.label || "")}" placeholder="${t("profile.home_ph")}" /></div>
        <div class="field"><label>${t("profile.recipient_name")}</label><input class="input" id="aname" value="${esc(addr?.recipient_name || "")}" /></div>
        <div class="field"><label>${t("profile.phone_req")}</label><input class="input" id="aphone" value="${esc(addr?.recipient_phone || "")}" /></div>
        <div class="field">
          <div class="row" style="justify-content:space-between;align-items:center;margin-bottom:6px">
            <label style="margin:0">${t("profile.address_req")}</label>
            <button class="btn btn-sm btn-outline" id="ageo-btn" type="button">&#128205; ${t("profile.use_location")}</button>
          </div>
          <textarea class="input" id="aaddr">${esc(addr?.address || "")}</textarea>
          <p class="small geo-status" id="ageo-status" hidden></p>
        </div>
        <label class="row" style="cursor:pointer;justify-content:flex-start;gap:10px;margin-bottom:12px">
          <input type="checkbox" id="adef" ${addr?.is_default ? "checked" : ""} />
          <span>${t("profile.use_default")}</span>
        </label>
        <div class="btn-row">
          <button class="btn btn-outline grow" id="addr-cancel">${t("ui.cancel")}</button>
          <button class="btn btn-primary grow" id="addr-save">${t("profile.save")}</button>
        </div>
      </div>`);
    form.querySelector("#addr-cancel").addEventListener("click", () => renderAddrList());
    form.querySelector("#addr-save").addEventListener("click", async () => {
      const payload = {
        label: form.querySelector("#alabel").value.trim() || null,
        recipient_name: form.querySelector("#aname").value.trim(),
        recipient_phone: form.querySelector("#aphone").value.trim(),
        address: form.querySelector("#aaddr").value.trim(),
        is_default: form.querySelector("#adef").checked,
      };
      if (!payload.recipient_name) return toast(t("profile.need_recipient"), "error");
      if (!payload.recipient_phone) return toast(t("profile.need_phone"), "error");
      if (payload.address.length < 5) return toast(t("profile.need_address"), "error");
      const btn = form.querySelector("#addr-save");
      btn.disabled = true;
      btn.textContent = t("profile.saving");
      try {
        if (addr) await api.patch(`/api/addresses/${addr.id}`, payload);
        else await api.post("/api/addresses", payload);
        toast(t("profile.saved_addr"), "success");
        renderAddrList();
      } catch (err) {
        toast(err.message, "error");
        btn.disabled = false;
        btn.textContent = t("profile.save");
      }
    });
    attachGeoButton(
      form.querySelector("#ageo-btn"),
      form.querySelector("#ageo-status"),
      form.querySelector("#aaddr")
    );
    addrList.appendChild(form);
  };

  host.querySelector("#addr-add").addEventListener("click", () => renderAddrForm(null));
  await renderAddrList();

  host.querySelectorAll("[data-admin]").forEach((b) => {
    b.addEventListener("click", () => navigate(b.dataset.admin));
  });
  host.querySelectorAll("[data-nav]").forEach((b) => {
    b.addEventListener("click", () => navigate(b.dataset.nav));
  });
  host.querySelector("#logout").addEventListener("click", () => logout());

  root.appendChild(host);
}
