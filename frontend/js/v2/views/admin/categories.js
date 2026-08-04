import { api } from "../../api.js";
import { navigate } from "../../router.js";
import { el, esc, toast, confirmBox, modal } from "../../ui.js";

export async function renderCategories(root) {
  root.innerHTML = "";
  const host = el(`
    <div class="container">
      <div class="row">
        <h1 class="title grow">Categories</h1>
        <button class="btn btn-primary btn-sm" id="new">+ New</button>
      </div>
      <div id="list"></div>
    </div>`);

  const list = host.querySelector("#list");
  const load = async () => {
    list.innerHTML = "";
    const cats = await api.get("/api/admin/categories");
    if (cats.length === 0) {
      list.appendChild(el(`<div class="empty"><span class="ico">&#128193;</span>No categories yet.</div>`));
      return;
    }
    for (const c of cats) {
      const row = el(`
        <div class="card">
          <div class="row">
            <div class="grow">
              <b style="font-size:14px">${esc(c.name)} ${c.is_active ? "" : '<span class="badge badge-cancelled">hidden</span>'}</b>
              <div class="small muted">${c.product_count} product(s) · /${esc(c.slug)}</div>
            </div>
            <div class="btn-row" style="margin:0">
              <button class="btn btn-sm btn-outline" data-edit>Edit</button>
              <button class="btn btn-sm btn-danger" data-del>Delete</button>
            </div>
          </div>
        </div>`);
      row.querySelector("[data-edit]").addEventListener("click", () => openEditor(c));
      row.querySelector("[data-del]").addEventListener("click", async () => {
        const ok = await confirmBox(`Delete category "${c.name}"? Products stay but lose this category.`, "Delete category");
        if (!ok) return;
        try {
          await api.del(`/api/admin/categories/${c.id}`);
          toast("Deleted", "success");
          load();
        } catch (err) {
          toast(err.message, "error");
        }
      });
      list.appendChild(row);
    }
  };

  function openEditor(cat = null) {
    const body = el(`
      <div>
        <div class="field"><label>Name *</label><input class="input" id="c-name" value="${esc(cat?.name || "")}" /></div>
        <div class="field"><label>Slug (auto if empty)</label><input class="input" id="c-slug" value="${esc(cat?.slug || "")}" /></div>
        <div class="field"><label>Description</label><textarea class="input" id="c-desc">${esc(cat?.description || "")}</textarea></div>
        <label class="row" style="cursor:pointer;justify-content:flex-start;gap:10px">
          <input type="checkbox" id="c-active" ${cat ? (cat.is_active ? "checked" : "") : "checked"} />
          <span>Visible in the shop</span>
        </label>
      </div>`);
    modal({
      title: cat ? "Edit category" : "New category",
      body,
      okText: "Save",
      onOk: async () => {
        const payload = {
          name: body.querySelector("#c-name").value.trim(),
          slug: body.querySelector("#c-slug").value.trim() || null,
          description: body.querySelector("#c-desc").value.trim() || null,
          is_active: body.querySelector("#c-active").checked,
        };
        if (!payload.name) throw new Error("Name is required");
        if (cat) {
          await api.patch(`/api/admin/categories/${cat.id}`, payload);
        } else {
          await api.post("/api/admin/categories", payload);
        }
        toast("Saved", "success");
        load();
      },
    });
  }

  host.querySelector("#new").addEventListener("click", () => openEditor());
  root.appendChild(host);
  await load();
}
