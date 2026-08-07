import { api } from "../../api.js";
import { el, esc, toast, confirmBox, modal, getStore } from "../../ui.js";

function fmtDate(v) {
  if (!v) return "—";
  return new Date(v).toLocaleString("en-US", { day: "2-digit", month: "short", year: "numeric" });
}

export async function renderCoupons(root) {
  root.innerHTML = "";
  const store = await getStore();
  if (!store.features?.coupons) {
    root.innerHTML = `<div class="container"><div class="empty"><span class="ico">&#127873;</span>Coupons are available on the Growth plan or higher. Upgrade to create discount codes.</div></div>`;
    return;
  }
  let state = { page: 1, pageSize: 50, search: "" };

  const host = el(`
    <div class="container">
      <div class="row">
        <h1 class="title grow">Coupons</h1>
        <button class="btn btn-primary btn-sm" id="new">+ New</button>
      </div>
      <input class="search" id="search" placeholder="Search codes…" />
      <div id="list"></div>
    </div>`);

  const list = host.querySelector("#list");

  const load = async () => {
    list.innerHTML = `<div class="skeleton" style="height:120px"></div>`;
    const params = new URLSearchParams({ page: state.page, page_size: state.pageSize });
    if (state.search) params.set("search", state.search);
    const data = await api.get(`/api/admin/coupons?${params}`);
    list.innerHTML = "";
    if (data.items.length === 0) {
      list.appendChild(el(`<div class="empty"><span class="ico">&#127873;</span>No coupons yet. Create one to offer discounts.</div>`));
      return;
    }
    for (const c of data.items) {
      const expired = c.active_until && new Date(c.active_until) < new Date();
      const label = c.discount_type === "percent" ? `${c.value}% off` : `${c.value} off`;
      const status = expired || !c.is_active ? `<span class="badge badge-cancelled">${c.is_active ? "expired" : "off"}</span>` : (c.max_uses !== null && c.used_count >= c.max_uses ? `<span class="badge badge-cancelled">used up</span>` : `<span class="badge badge-completed">active</span>`);
      const row = el(`
        <div class="card">
          <div class="row">
            <div class="grow" style="min-width:0">
              <div class="row">
                <b style="font-size:14px;letter-spacing:.5px">${esc(c.code)}</b>
                ${status}
              </div>
              <div class="small muted">${label} · min ${c.min_subtotal} · ${c.used_count}/${c.max_uses ?? "∞"} used${c.per_user_limit > 1 ? ` · ${c.per_user_limit}/user` : ""}</div>
              <div class="small muted">${fmtDate(c.active_from)} → ${fmtDate(c.active_until)}</div>
            </div>
            <div class="btn-row" style="margin:0">
              <button class="btn btn-sm btn-outline" data-edit>Edit</button>
              <button class="btn btn-sm btn-danger" data-del>Delete</button>
            </div>
          </div>
        </div>`);
      row.querySelector("[data-edit]").addEventListener("click", () => openEditor(c));
      row.querySelector("[data-del]").addEventListener("click", async () => {
        const ok = await confirmBox(`Delete coupon "${c.code}"?`, "Delete coupon");
        if (!ok) return;
        try {
          await api.del(`/api/admin/coupons/${c.id}`);
          toast("Deleted", "success");
          load();
        } catch (err) {
          toast(err.message, "error");
        }
      });
      list.appendChild(row);
    }
  };

  function openEditor(c = null) {
    const body = el(`
      <div>
        <div class="field"><label>Code *</label><input class="input" id="c-code" value="${esc(c?.code || "")}" placeholder="e.g. SAVE10" style="text-transform:uppercase" /></div>
        <div class="field"><label>Discount type</label>
          <select class="input" id="c-type">
            <option value="percent" ${c?.discount_type === "percent" ? "selected" : ""}>Percent (%)</option>
            <option value="fixed" ${c?.discount_type === "fixed" ? "selected" : ""}>Fixed amount</option>
          </select>
        </div>
        <div class="field"><label>Value *</label><input class="input" id="c-value" type="number" step="0.01" min="0.01" value="${c?.value ?? ""}" /></div>
        <div class="field"><label>Minimum order subtotal</label><input class="input" id="c-min" type="number" step="0.01" min="0" value="${c?.min_subtotal ?? 0}" /></div>
        <div class="field"><label>Maximum total uses (leave empty for unlimited)</label><input class="input" id="c-max" type="number" min="1" value="${c?.max_uses ?? ""}" placeholder="Unlimited" /></div>
        <div class="field"><label>Uses per customer</label><input class="input" id="c-per" type="number" min="1" value="${c?.per_user_limit ?? 1}" /></div>
        <div class="field"><label>Active from (optional)</label><input class="input" id="c-from" type="datetime-local" value="${c?.active_from ? c.active_from.slice(0, 16) : ""}" /></div>
        <div class="field"><label>Active until (optional)</label><input class="input" id="c-until" type="datetime-local" value="${c?.active_until ? c.active_until.slice(0, 16) : ""}" /></div>
        <label class="row" style="cursor:pointer;justify-content:flex-start;gap:10px">
          <input type="checkbox" id="c-active" ${c === null || c.is_active ? "checked" : ""} />
          <span>Active</span>
        </label>
      </div>`);
    modal({
      title: c ? `Edit ${c.code}` : "New coupon",
      body,
      okText: "Save",
      onOk: async () => {
        const payload = {
          code: body.querySelector("#c-code").value.trim().toUpperCase(),
          discount_type: body.querySelector("#c-type").value,
          value: Number(body.querySelector("#c-value").value),
          min_subtotal: Number(body.querySelector("#c-min").value || 0),
          max_uses: body.querySelector("#c-max").value === "" ? null : Number(body.querySelector("#c-max").value),
          per_user_limit: Number(body.querySelector("#c-per").value || 1),
          active_from: body.querySelector("#c-from").value || null,
          active_until: body.querySelector("#c-until").value || null,
          is_active: body.querySelector("#c-active").checked,
        };
        if (!payload.code) throw new Error("Code is required");
        if (!payload.value || payload.value <= 0) throw new Error("Value is required");
        if (payload.discount_type === "percent" && payload.value > 100) throw new Error("Percent cannot exceed 100");
        if (c) {
          await api.patch(`/api/admin/coupons/${c.id}`, payload);
        } else {
          await api.post("/api/admin/coupons", payload);
        }
        toast("Saved", "success");
        load();
      },
    });
  }

  let debounce = null;
  host.querySelector("#search").addEventListener("input", (e) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => { state.search = e.target.value.trim(); state.page = 1; load(); }, 300);
  });
  host.querySelector("#new").addEventListener("click", () => openEditor());
  root.appendChild(host);
  await load();
}
