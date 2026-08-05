import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, getStore, toast, confirmBox } from "../ui.js";
import { logout } from "../auth.js";

export async function renderProfile(root) {
  root.innerHTML = "";
  const store = await getStore();
  const me = await api.get("/api/me");

  const initials = (me.first_name?.[0] || "") + (me.last_name?.[0] || "") || "U";
  const host = el(`
    <div class="container">
      <div class="profile-hero">
        <div class="avatar">${me.photo_url ? `<img src="${esc(me.photo_url)}" />` : esc(initials)}</div>
        <h1>${esc(me.display_name || me.first_name || "User")}</h1>
        <p>${me.username ? "@" + esc(me.username) : `Telegram ID ${me.telegram_id}`}</p>
        ${me.role === "admin" ? `<div style="position:relative;z-index:1;margin-top:8px"><span class="tag" style="background:rgba(255,255,255,0.2);color:#fff">Store owner</span></div>` : ""}
      </div>

      <div class="card section-title">Contact & delivery details</div>
      <div class="card">
        <div class="field"><label>Phone</label><input class="input" id="phone" value="${esc(me.phone || "")}" placeholder="+855 …" /></div>
        <div class="field"><label>Default address</label><textarea class="input" id="address" placeholder="Your default delivery address">${esc(me.address || "")}</textarea></div>
        <button class="btn btn-primary" id="save">Save details</button>
      </div>

      <div class="card section-title">Saved addresses</div>
      <div class="card">
        <div id="addr-list"></div>
        <button class="btn btn-outline btn-sm" id="addr-add" style="margin-top:8px">+ Add address</button>
      </div>

      ${me.role !== "admin" ? `
      <div class="card section-title">My account</div>
      <div class="card" style="padding:4px 14px">
        <button class="menu-item" data-nav="orders"><span class="menu-ico">&#128203;</span>My orders<span class="menu-chev">›</span></button>
        <button class="menu-item" data-nav="wishlist"><span class="menu-ico">&#10084;&#65039;</span>Wishlist<span class="menu-chev">›</span></button>
      </div>` : ""}

      ${me.role === "admin" ? `
      <div class="card section-title">Store management</div>
      <div class="card" style="padding:4px 14px">
        <button class="menu-item" data-admin="admin"><span class="menu-ico">&#128200;</span>Dashboard<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/products"><span class="menu-ico">&#128230;</span>Products<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/orders"><span class="menu-ico">&#128203;</span>Orders<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/customers"><span class="menu-ico">&#128101;</span>Customers<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/categories"><span class="menu-ico">&#128193;</span>Categories<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/coupons"><span class="menu-ico">&#127991;</span>Coupons<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/reviews"><span class="menu-ico">&#11088;</span>Reviews<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/broadcasts"><span class="menu-ico">&#128227;</span>Broadcasts<span class="menu-chev">›</span></button>
        <button class="menu-item" data-admin="admin/settings"><span class="menu-ico">&#9881;</span>Settings<span class="menu-chev">›</span></button>
      </div>` : ""}

      <button class="btn btn-danger" id="logout" style="margin-top:14px">Log out</button>
      <footer class="page-footer">${esc(store.store_name)}</footer>
    </div>`);

  host.querySelector("#save").addEventListener("click", async () => {
    try {
      await api.patch("/api/me", {
        phone: host.querySelector("#phone").value.trim() || null,
        address: host.querySelector("#address").value.trim() || null,
      });
      toast("Saved", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

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
      addrList.appendChild(el(`<p class="muted small">No saved addresses yet.</p>`));
    }
    for (const a of items) {
      const row = el(`
        <div style="padding:10px 0;border-bottom:1px solid var(--border)">
          <div class="row">
            <div class="grow" style="min-width:0">
              <div class="row">
                <b style="font-size:13px">${esc(a.label || "Address")}</b>
                ${a.is_default ? `<span class="tag" style="background:var(--green-bg);color:var(--green)">Default</span>` : ""}
              </div>
              <div class="small muted" style="margin-top:2px">${esc(a.recipient_name)} · ${esc(a.recipient_phone)}</div>
              <div class="small muted">${esc(a.address)}</div>
            </div>
          </div>
          <div class="btn-row" style="margin-top:8px">
            ${a.is_default ? "" : `<button class="btn btn-sm btn-outline" data-set="${a.id}">Set default</button>`}
            <button class="btn btn-sm btn-outline" data-edit="${a.id}">Edit</button>
            <button class="btn btn-sm btn-danger" data-del="${a.id}">Delete</button>
          </div>
        </div>`);
      row.querySelector("[data-set]")?.addEventListener("click", async () => {
        try {
          await api.patch(`/api/addresses/${a.id}`, { is_default: true });
          toast("Default address set", "success");
          renderAddrList();
        } catch (err) {
          toast(err.message, "error");
        }
      });
      row.querySelector("[data-edit]")?.addEventListener("click", () => renderAddrForm(a));
      row.querySelector("[data-del]")?.addEventListener("click", async () => {
        const ok = await confirmBox("Delete this saved address?", "Delete address");
        if (!ok) return;
        try {
          await api.del(`/api/addresses/${a.id}`);
          toast("Address deleted", "success");
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
        <div class="field"><label>Label (e.g. Home)</label><input class="input" id="alabel" value="${esc(addr?.label || "")}" placeholder="Home" /></div>
        <div class="field"><label>Recipient name *</label><input class="input" id="aname" value="${esc(addr?.recipient_name || "")}" /></div>
        <div class="field"><label>Phone *</label><input class="input" id="aphone" value="${esc(addr?.recipient_phone || "")}" /></div>
        <div class="field"><label>Address *</label><textarea class="input" id="aaddr">${esc(addr?.address || "")}</textarea></div>
        <label class="row" style="cursor:pointer;justify-content:flex-start;gap:10px;margin-bottom:12px">
          <input type="checkbox" id="adef" ${addr?.is_default ? "checked" : ""} />
          <span>Use as default address</span>
        </label>
        <div class="btn-row">
          <button class="btn btn-outline grow" id="addr-cancel">Cancel</button>
          <button class="btn btn-primary grow" id="addr-save">Save</button>
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
      if (!payload.recipient_name) return toast("Enter a recipient name", "error");
      if (!payload.recipient_phone) return toast("Enter a phone number", "error");
      if (payload.address.length < 5) return toast("Enter a valid address", "error");
      const btn = form.querySelector("#addr-save");
      btn.disabled = true;
      btn.textContent = "Saving…";
      try {
        if (addr) await api.patch(`/api/addresses/${addr.id}`, payload);
        else await api.post("/api/addresses", payload);
        toast("Address saved", "success");
        renderAddrList();
      } catch (err) {
        toast(err.message, "error");
        btn.disabled = false;
        btn.textContent = "Save";
      }
    });
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
