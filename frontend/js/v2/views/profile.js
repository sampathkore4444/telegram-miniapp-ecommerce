import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, getStore, toast } from "../ui.js";
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

  host.querySelectorAll("[data-admin]").forEach((b) => {
    b.addEventListener("click", () => navigate(b.dataset.admin));
  });
  host.querySelectorAll("[data-nav]").forEach((b) => {
    b.addEventListener("click", () => navigate(b.dataset.nav));
  });
  host.querySelector("#logout").addEventListener("click", () => logout());

  root.appendChild(host);
}
