import { api } from "../../api.js";
import { navigate } from "../../router.js";
import { el, esc, toast, modal, getStore, confirmBox } from "../../ui.js";
import { setStoreSlug, getStoreSlug } from "../../store.js";

export async function renderStores(root) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:240px"></div></div>`;
  const store = await getStore();
  const stores = await api.get("/api/admin/stores");
  const canCreate = stores.length === 0 || Boolean(store.features?.multi_store);

  const host = el(`
    <div class="container">
      <div class="row">
        <h1 class="title grow">Stores</h1>
        ${canCreate
          ? `<button class="btn btn-primary btn-sm" id="new-store">+ New store</button>`
          : `<span class="tag" title="Multiple stores require the Pro plan">Pro feature</span>`}
      </div>
      <p class="small muted" style="margin-bottom:12px">Every store has its own products, orders, customers and link. Your first store is free; extra stores need the Pro plan.</p>
      <div id="list"></div>
    </div>`);

  const list = host.querySelector("#list");
  const current = getStoreSlug();

  const renderList = () => {
    list.innerHTML = "";
    if (stores.length === 0) {
      list.appendChild(el(`<div class="empty"><span class="ico">&#127983;</span>No stores yet — create your first one.</div>`));
      return;
    }
    for (const s of stores) {
      const isCurrent = s.slug === current;
      const row = el(`
        <div class="card">
          <div class="row">
            <div class="grow" style="min-width:0">
              <div class="row" style="justify-content:flex-start;gap:8px">
                <b style="font-size:14px">${esc(s.name)}</b>
                ${isCurrent ? `<span class="tag" style="background:var(--green-bg);color:var(--green)">active</span>` : ""}
                ${s.is_active ? "" : '<span class="badge badge-cancelled">inactive</span>'}
              </div>
              <div class="small muted" style="margin-top:3px">/${esc(s.slug)} · ${s.product_count} product(s) · ${esc(s.plan)} plan</div>
            </div>
            <div class="btn-row" style="margin:0">
              <button class="btn btn-sm btn-outline" data-open>Open</button>
              ${isCurrent ? "" : `<button class="btn btn-sm btn-primary" data-switch>Manage</button>`}
              <button class="btn btn-sm btn-danger" data-del>Delete</button>
            </div>
          </div>
        </div>`);
      row.querySelector("[data-open]").addEventListener("click", () => navigate(`s/${s.slug}`));
      row.querySelector("[data-switch]")?.addEventListener("click", () => {
        setStoreSlug(s.slug);
        navigate("admin");
      });
      row.querySelector("[data-del]").addEventListener("click", async () => {
        const ok = await confirmBox(`Delete store "${s.name}"? This can't be undone.`, "Delete store");
        if (!ok) return;
        try {
          await api.del(`/api/admin/stores/${s.id}`);
          toast("Store deleted", "success");
          const idx = stores.findIndex((x) => x.id === s.id);
          if (idx > -1) stores.splice(idx, 1);
          if (isCurrent) {
            setStoreSlug(stores[0]?.slug || "");
          } else {
            renderList();
          }
        } catch (err) {
          toast(err.message, "error");
        }
      });
      list.appendChild(row);
    }
  };

  function openNewStore() {
    const body = el(`
      <div>
        <div class="field"><label>Store name *</label><input class="input" id="s-name" maxlength="120" placeholder="e.g. My Shop" /></div>
        <div class="field"><label>Slug (link) — optional</label><input class="input" id="s-slug" maxlength="120" placeholder="auto-generated" /></div>
        <p class="small muted">The slug becomes your store's link — e.g. <code>/s/<b id="s-preview">my-shop</b></code>. Use lowercase letters, numbers and dashes.</p>
      </div>`);
    const name = body.querySelector("#s-name");
    const slug = body.querySelector("#s-slug");
    const preview = body.querySelector("#s-preview");
    const cleanSlug = (v) => String(v || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    const updatePreview = () => { preview.textContent = cleanSlug(slug.value) || "auto-generated"; };
    slug.addEventListener("input", updatePreview);
    updatePreview();
    modal({
      title: "New store",
      body,
      okText: "Create store",
      onOk: async () => {
        const storeName = name.value.trim();
        if (!storeName) throw new Error("Store name is required");
        const created = await api.post("/api/admin/stores", {
          name: storeName,
          slug: cleanSlug(slug.value) || null,
        });
        toast("Store created", "success");
        setStoreSlug(created.slug);
        navigate("admin");
      },
    });
  }

  host.querySelector("#new-store")?.addEventListener("click", openNewStore);
  root.innerHTML = "";
  root.appendChild(host);
  renderList();
}
