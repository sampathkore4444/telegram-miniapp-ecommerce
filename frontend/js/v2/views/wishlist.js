import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, money, getStore, toast, emptyState } from "../ui.js";
import { t } from "../i18n.js";

export async function renderWishlist(root) {
  root.innerHTML = "";
  const store = await getStore();
  const host = el(`
    <div class="container">
      <h1 class="title">${t("wishlist.title")}</h1>
      <div id="list"></div>
    </div>`);

  const list = host.querySelector("#list");

  const load = async () => {
    list.innerHTML = "";
    const data = await api.get("/api/wishlist");
    if (data.items.length === 0) {
      list.appendChild(emptyState("&#10084;&#65039;", t("wishlist.empty_title"), t("wishlist.empty_sub")));
      return;
    }
    for (const item of data.items) {
      const p = item.product;
      if (!p) continue;
      const img = p.images && p.images.length
        ? `<img loading="lazy" src="${esc(p.images[0])}" data-err="hide">`
        : `<span class="ph">&#128230;</span>`;
      const row = el(`
        <div class="card" data-nav style="cursor:pointer">
          <div class="row">
            <div class="img-wrap" style="width:64px;height:64px;flex:none;border-radius:12px;overflow:hidden;background:var(--bg-soft)">${img}</div>
            <div class="grow" style="min-width:0">
              <b style="font-size:14px">${esc(p.name)}</b>
              <div class="small muted">${money(p.price, store)}${p.in_stock ? "" : ` · <span style="color:var(--red)">${t("wishlist.sold_out")}</span>`}</div>
            </div>
            <button class="btn btn-sm btn-outline" data-remove style="align-self:flex-start">${t("wishlist.remove")}</button>
          </div>
        </div>`);
      row.querySelector("[data-nav]").addEventListener("click", (e) => {
        if (e.target.closest("[data-remove]")) return;
        navigate(`product/${p.id}`);
      });
      row.querySelector("[data-remove]").addEventListener("click", async () => {
        try {
          await api.del(`/api/wishlist/${p.id}`);
          toast(t("wishlist.removed"), "success");
          load();
        } catch (err) {
          toast(err.message, "error");
        }
      });
      list.appendChild(row);
    }
  };

  root.appendChild(host);
  await load();
}
