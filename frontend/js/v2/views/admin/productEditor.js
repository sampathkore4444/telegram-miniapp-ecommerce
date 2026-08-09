import { api } from "../../api.js";
import { navigate } from "../../router.js";
import { el, esc, toast } from "../../ui.js";

function optionsToStr(o) {
  if (!o) return "";
  return Object.entries(o).map(([k, v]) => `${k}: ${v}`).join(", ");
}

function parseOptions(str) {
  if (!str) return {};
  const t = str.trim();
  if (!t) return {};
  if (t.startsWith("{")) {
    try { return JSON.parse(t); } catch { return {}; }
  }
  const out = {};
  t.split(",").forEach((part) => {
    const i = part.indexOf(":");
    if (i > 0) out[part.slice(0, i).trim()] = part.slice(i + 1).trim();
    else if (part.trim()) out[part.trim()] = part.trim();
  });
  return out;
}

export async function renderProductEditor(root, params) {
  root.innerHTML = "";
  const isNew = !params.id || params.id === "new";
  const categories = await api.get("/api/admin/categories");
  let product = { images: [], category_id: "", name: "", description: "", price: "", compare_at_price: "", sku: "", stock: 0, status: "draft", is_featured: false };
  let tiers = [];
  let variants = [];

  if (!isNew) {
    const d = await api.get(`/api/admin/products/${params.id}`);
    product = {
      images: d.images || [],
      category_id: d.category_id || "",
      name: d.name,
      description: d.description || "",
      price: d.price,
      compare_at_price: d.compare_at_price ?? "",
      sku: d.sku || "",
      stock: d.stock,
      status: d.status,
      is_featured: d.is_featured,
    };
    tiers = (d.price_tiers || []).map((t) => ({ min_quantity: t.min_quantity, price: t.price }));
    variants = (d.variants || []).map((v) => ({
      id: v.id ?? null,
      name: v.name || "",
      optionsText: optionsToStr(v.options),
      priceText: v.price != null ? v.price : "",
      stock: v.stock ?? 0,
      is_active: v.is_active !== false,
    }));
  }

  const catOptions = categories.map((c) => `<option value="${c.id}" ${Number(product.category_id) === c.id ? "selected" : ""}>${esc(c.name)}</option>`).join("");

  const host = el(`
    <div class="container">
      <button class="btn btn-outline btn-sm" id="back" style="margin-bottom:10px">← Back</button>
      <h1 class="title">${isNew ? "New product" : "Edit product"}</h1>

      <div class="card section-title">Images</div>
      <div class="card">
        <div id="thumbs" class="thumb-grid"></div>
        <input type="file" id="img-input" accept="image/*" style="display:none" />
        <button class="btn btn-outline btn-sm" id="add-img" style="margin-top:10px">+ Add image</button>
      </div>

      <div class="card section-title">Details</div>
      <div class="card">
        <div class="field"><label>Name *</label><input class="input" id="name" value="${esc(product.name)}" /></div>
        <div class="field"><label>Category</label><select class="select" id="category"><option value="">— None —</option>${catOptions}</select></div>
        <div class="field"><label>Description</label><textarea class="input" id="desc">${esc(product.description)}</textarea></div>
      </div>

      <div class="card section-title">Pricing & stock</div>
      <div class="card">
        <div class="field"><label>Price *</label><input class="input" type="number" step="0.01" min="0" id="price" value="${esc(product.price)}" /></div>
        <div class="field"><label>Compare-at price (optional)</label><input class="input" type="number" step="0.01" min="0" id="compare" value="${esc(product.compare_at_price)}" /></div>
        <div class="field"><label>SKU</label><input class="input" id="sku" value="${esc(product.sku)}" /></div>
        <div class="field"><label>Stock</label><input class="input" type="number" min="0" id="stock" value="${esc(product.stock)}" /></div>
        <div class="row" style="margin-bottom:12px">
          <span class="row-label">Status</span>
          <select class="select" id="status" style="width:auto">
            <option value="draft" ${product.status === "draft" ? "selected" : ""}>Draft</option>
            <option value="active" ${product.status === "active" ? "selected" : ""}>Active</option>
            <option value="archived" ${product.status === "archived" ? "selected" : ""}>Archived</option>
          </select>
        </div>
        <label class="row" style="cursor:pointer;justify-content:flex-start;gap:10px">
          <input type="checkbox" id="featured" ${product.is_featured ? "checked" : ""} />
          <span>Feature this product on the home page</span>
        </label>
      </div>

      <div class="card section-title">Quantity discount tiers</div>
      <div class="card">
        <p class="small muted" style="margin-bottom:10px">Tier price applies when a buyer's quantity reaches the minimum. Variant prices still override tiers.</p>
        <div id="tiers"></div>
        <button class="btn btn-outline btn-sm" id="add-tier" style="margin-top:10px">+ Add tier</button>
      </div>

      <div class="card section-title">Variants</div>
      <div class="card">
        <p class="small muted" style="margin-bottom:10px">Optional size/color options. Leave price blank to inherit the product price; stock here overrides product stock.</p>
        <div id="variants"></div>
        <button class="btn btn-outline btn-sm" id="add-variant" style="margin-top:10px">+ Add variant</button>
      </div>

      <button class="btn btn-primary" id="save">Save product</button>
    </div>`);

  const thumbs = host.querySelector("#thumbs");
  const renderThumbs = () => {
    thumbs.innerHTML = "";
    product.images.forEach((url, idx) => {
      const t = el(`
        <div class="thumb">
          <img src="${esc(url)}" data-err="parent" />
          <button class="x" data-idx="${idx}">×</button>
        </div>`);
      t.querySelector(".x").addEventListener("click", () => {
        product.images.splice(idx, 1);
        renderThumbs();
      });
      thumbs.appendChild(t);
    });
  };

  host.querySelector("#add-img").addEventListener("click", () => host.querySelector("#img-input").click());
  host.querySelector("#img-input").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await api.upload("/api/admin/uploads?purpose=products", fd);
      product.images.push(res.url);
      renderThumbs();
      toast("Image added", "success");
    } catch (err) {
      toast(err.message, "error");
    }
    e.target.value = "";
  });

  const tiersEl = host.querySelector("#tiers");
  const renderTiers = () => {
    tiersEl.innerHTML = "";
    tiers.forEach((t, idx) => {
      const row = el(`
        <div class="row" style="gap:6px;margin-bottom:8px">
          <input class="input" type="number" min="2" placeholder="Min qty" data-f="min_quantity" value="${esc(t.min_quantity)}" style="width:110px" />
          <input class="input" type="number" step="0.01" min="0" placeholder="Price" data-f="price" value="${esc(t.price)}" />
          <button class="x" data-idx="${idx}">×</button>
        </div>`);
      row.querySelector("[data-f='min_quantity']").addEventListener("input", (e) => { tiers[idx].min_quantity = e.target.value; });
      row.querySelector("[data-f='price']").addEventListener("input", (e) => { tiers[idx].price = e.target.value; });
      row.querySelector("[data-idx]").addEventListener("click", () => { tiers.splice(idx, 1); renderTiers(); });
      tiersEl.appendChild(row);
    });
  };
  host.querySelector("#add-tier").addEventListener("click", () => {
    tiers.push({ min_quantity: "", price: "" });
    renderTiers();
  });

  const variantsEl = host.querySelector("#variants");
  const renderVariants = () => {
    variantsEl.innerHTML = "";
    variants.forEach((v, idx) => {
      const row = el(`
        <div style="border:1px solid var(--border);border-radius:12px;padding:10px;margin-bottom:10px;background:var(--bg)">
          <div class="row" style="gap:6px">
            <input class="input grow" data-f="name" placeholder="Variant name * (e.g. Red / M)" value="${esc(v.name)}" />
            <input class="input" data-f="stock" type="number" min="0" placeholder="Stock" value="${esc(v.stock)}" style="width:90px" />
            <button class="x" data-idx="${idx}">×</button>
          </div>
          <div class="row" style="gap:6px;margin-top:6px">
            <input class="input grow" data-f="options" placeholder="Options (Color: Red, Size: M)" value="${esc(v.optionsText)}" />
            <input class="input" data-f="price" type="number" step="0.01" min="0" placeholder="Price (blank = product)" value="${esc(v.priceText)}" style="width:150px" />
          </div>
          <label class="row" style="justify-content:flex-start;gap:8px;margin-top:8px;font-size:13px;cursor:pointer">
            <input type="checkbox" data-f="is_active" ${v.is_active ? "checked" : ""} />
            <span class="muted">Active (visible to buyers)</span>
          </label>
        </div>`);
      row.querySelector("[data-f='name']").addEventListener("input", (e) => { v.name = e.target.value; });
      row.querySelector("[data-f='stock']").addEventListener("input", (e) => { v.stock = e.target.value; });
      row.querySelector("[data-f='options']").addEventListener("input", (e) => { v.optionsText = e.target.value; });
      row.querySelector("[data-f='price']").addEventListener("input", (e) => { v.priceText = e.target.value; });
      row.querySelector("[data-f='is_active']").addEventListener("change", (e) => { v.is_active = e.target.checked; });
      row.querySelector("[data-idx]").addEventListener("click", () => { variants.splice(idx, 1); renderVariants(); });
      variantsEl.appendChild(row);
    });
  };
  host.querySelector("#add-variant").addEventListener("click", () => {
    variants.push({ id: null, name: "", optionsText: "", priceText: "", stock: 0, is_active: true });
    renderVariants();
  });

  host.querySelector("#back").addEventListener("click", () => navigate("admin/products"));
  host.querySelector("#save").addEventListener("click", async () => {
    const payload = {
      name: host.querySelector("#name").value.trim(),
      category_id: host.querySelector("#category").value ? Number(host.querySelector("#category").value) : null,
      description: host.querySelector("#desc").value.trim() || null,
      price: Number(host.querySelector("#price").value),
      compare_at_price: host.querySelector("#compare").value ? Number(host.querySelector("#compare").value) : null,
      sku: host.querySelector("#sku").value.trim() || null,
      stock: Number(host.querySelector("#stock").value || 0),
      status: host.querySelector("#status").value,
      is_featured: host.querySelector("#featured").checked,
      images: product.images,
      price_tiers: tiers
        .map((t) => ({ min_quantity: Number(t.min_quantity || 0), price: Number(t.price || 0) }))
        .filter((t) => t.min_quantity >= 2 && t.price > 0),
      variants: variants
        .filter((v) => v.name.trim())
        .map((v) => ({
          id: v.id ?? null,
          name: v.name.trim(),
          options: parseOptions(v.optionsText),
          price: v.priceText !== "" ? Number(v.priceText) : null,
          compare_at_price: null,
          sku: null,
          stock: Number(v.stock || 0),
          is_active: v.is_active,
        })),
    };
    if (!payload.name) return toast("Name is required", "error");
    if (!(payload.price > 0)) return toast("Enter a valid price", "error");

    try {
      if (isNew) {
        await api.post("/api/admin/products", payload);
        toast("Product created", "success");
      } else {
        await api.patch(`/api/admin/products/${params.id}`, payload);
        toast("Saved", "success");
      }
      navigate("admin/products");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  root.appendChild(host);
  renderThumbs();
  renderTiers();
  renderVariants();
}
