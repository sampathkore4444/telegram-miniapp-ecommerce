import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, money, getStore, toast, applyCountBadge, shareToTelegram, productDeepLink, starRow, modal } from "../ui.js";
import { t, getLang, LANG_META } from "../i18n.js";

export async function renderProduct(root, params) {
  root.innerHTML = `<div class="container"><div class="skeleton" style="height:300px"></div></div>`;
  const store = await getStore();
  const product = await api.get(`/api/products/${params.id}`, false);

  const images = (product.images && product.images.length ? product.images : []);
  const variants = product.variants || [];
  const tiers = (product.price_tiers || []).slice().sort((a, b) => a.min_quantity - b.min_quantity);
  let selectedVariant = null;
  if (variants.length) {
    selectedVariant = variants.find((v) => v.in_stock) || variants[0];
  }

  const basePrice = () => (selectedVariant && selectedVariant.price != null ? selectedVariant.price : product.price);
  const comparePrice = () => (selectedVariant && selectedVariant.compare_at_price != null ? selectedVariant.compare_at_price : product.compare_at_price);
  const unitPrice = () => {
    let tier = null;
    for (const t of tiers) if (qty >= t.min_quantity) tier = t;
    return tier ? tier.price : basePrice();
  };
  const isAvailable = () => (variants.length ? (selectedVariant ? selectedVariant.in_stock : false) : product.in_stock);
  const availableStock = () => (variants.length ? (selectedVariant ? selectedVariant.stock : 0) : product.stock);

  const thumbs = images.length > 1
    ? `<div class="gallery-thumbs">${images.map((src, i) => `<button class="gthumb ${i === 0 ? "active" : ""}" data-i="${i}"><img src="${esc(src)}" alt="" onerror="this.remove()"></button>`).join("")}</div>`
    : "";

  let wishlisted = false;
  try {
    const wishlist = await api.get("/api/wishlist");
    wishlisted = wishlist.items.some((i) => i.product_id === product.id);
  } catch { /* guest */ }

  const reviewsRes = await api.get(`/api/products/${params.id}/reviews`, false);
  const reviews = reviewsRes.items || [];
  const summary = reviewsRes.summary || { average: 0, count: 0 };

  const host = el(`
    <div class="container sticky-page">
      <div class="card prod-gallery" style="padding:0;overflow:hidden">
        <div class="main-img" id="main"><span id="gallery-badge"></span>${images.length ? `<img src="${esc(images[0])}" alt="${esc(product.name)}">` : `<span style="font-size:80px">&#128230;</span>`}</div>
        ${thumbs}
        <button class="wish-btn ${wishlisted ? "active" : ""}" id="wish" aria-label="${t("product.add_to_wishlist")}" title="${t("product.wishlist_title")}">
          <svg viewBox="0 0 24 24" fill="${wishlisted ? "currentColor" : "none"}" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-4.6-9.3-9A5.4 5.4 0 0 1 12 6.3 5.4 5.4 0 0 1 21.3 12C19 16.4 12 21 12 21z"/></svg>
        </button>
        <button class="share-btn" id="share" aria-label="${t("product.share_aria")}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>
        </button>
      </div>

      <div class="card">
        <div class="row wrap">
          <h1 class="grow" style="font-size:19px;font-weight:800;line-height:1.3">${esc(product.name)}</h1>
          ${product.is_featured ? `<span class="tag tag-featured">${t("ui.featured")}</span>` : ""}
        </div>
        <div class="row" style="margin-top:10px">
          <span class="total-line" id="price" style="color:var(--accent);font-size:22px"></span>
          <span id="price-compare"></span>
        </div>
        <div id="tier-hint" class="small muted" style="margin-top:4px"></div>
        <div id="variants" class="chips" style="margin-top:10px;padding:2px 0 6px"></div>
        ${summary.count ? `<div class="row" style="margin-top:6px;align-items:center;gap:6px"><button class="link-like" id="scroll-reviews" style="background:none;border:none;padding:0;color:inherit;cursor:pointer">${starRow(summary.average)}</button><span class="small muted">${summary.average.toFixed(1)} · ${t("product.review_count", { n: summary.count })}</span></div>` : ""}
        <div class="small muted" id="stock-line" style="margin-top:8px"></div>
        ${product.description ? `<div class="divider"></div><p class="muted" style="font-size:14px;white-space:pre-wrap;line-height:1.6">${esc(product.description)}</p>` : ""}
      </div>

      <div id="reviews-section" class="card">
        <div class="row" style="align-items:center">
          <div class="grow"><b>${t("product.reviews_title")}</b></div>
          <button class="btn btn-sm btn-outline" id="write-review">${t("product.write_review")}</button>
        </div>
        ${summary.count ? `
        <div class="row" style="margin-top:10px;align-items:center;gap:10px">
          <span class="total-line" style="font-size:26px">${summary.average.toFixed(1)}</span>
          <div class="grow">
            ${starRow(summary.average, 16)}
            <div class="small muted">${t("product.rating_count", { n: summary.count })}</div>
          </div>
        </div>
        <div class="divider"></div>
        ${reviews.map((r) => `
          <div class="review-item">
            <div class="row" style="align-items:center">
              <div class="grow"><b style="font-size:13px">${esc(r.user_name)}</b></div>
              <span class="small muted">${esc(r.created_at ? new Date(r.created_at).toLocaleDateString(LANG_META[getLang()].locale, { day: "2-digit", month: "short", year: "numeric" }) : "")}</span>
            </div>
            <div class="small" style="margin-top:4px">${starRow(r.rating)}</div>
            ${r.comment ? `<p class="muted" style="font-size:14px;margin-top:6px;white-space:pre-wrap">${esc(r.comment)}</p>` : ""}
            ${r.images && r.images.length ? `<div class="row" style="margin-top:6px;gap:6px">${r.images.slice(0, 4).map((src) => `<img src="${esc(src)}" style="width:52px;height:52px;border-radius:8px;object-fit:cover" onerror="this.remove()">`).join("")}</div>` : ""}
          </div>`).join("")}` : `
        <p class="muted small" style="margin-top:10px">${t("product.no_reviews")}</p>`}
      </div>

      <footer class="page-footer">${esc(store.store_name)}</footer>

      <div class="sticky-bar">
        <div class="sticky-inner">
          <div class="qty" id="qty">
            <button data-step="-1">−</button><span id="qty-val">1</span><button data-step="1">+</button>
          </div>
          <button class="btn btn-outline grow" id="add-cart">${t("ui.add_to_cart")}</button>
          <button class="btn btn-primary grow" id="buy-now">${t("product.buy_now")}</button>
          <button class="btn btn-primary grow" id="notify" style="display:none">${t("product.notify_me")}</button>
        </div>
      </div>
    </div>`);

  let qty = 1;
  let subscribed = false;

  const qtyBox = host.querySelector("#qty");
  const qtyVal = host.querySelector("#qty-val");
  const addBtn = host.querySelector("#add-cart");
  const buyBtn = host.querySelector("#buy-now");
  const notifyBtn = host.querySelector("#notify");
  const priceEl = host.querySelector("#price");
  const priceCmp = host.querySelector("#price-compare");
  const galleryBadge = host.querySelector("#gallery-badge");
  const tierHint = host.querySelector("#tier-hint");
  const stockLine = host.querySelector("#stock-line");
  const variantsBox = host.querySelector("#variants");

  function updatePricing() {
    const price = unitPrice();
    const cmp = comparePrice();
    const onSale = cmp && cmp > price;
    priceEl.textContent = money(price, store);
    priceCmp.innerHTML = onSale
      ? `<span class="compare" style="text-decoration:line-through;color:var(--text-3);font-weight:500">${money(cmp, store)}</span>`
      : "";
    galleryBadge.innerHTML = onSale
      ? `<span class="sale-badge">-${Math.round(((cmp - price) / cmp) * 100)}%</span>`
      : "";
    tierHint.innerHTML = tiers.length
      ? t("product.tier_pricing", { list: tiers.map((t) => `${t.min_quantity}+ → ${money(t.price, store)}`).join(" · ") })
      : "";
    tierHint.style.display = tiers.length ? "" : "none";
  }

  function updateStock() {
    const cat = product.category ? ` · ${esc(product.category)}` : "";
    if (variants.length && selectedVariant) {
      stockLine.innerHTML = (selectedVariant.in_stock
        ? `<span style="color:var(--green);font-weight:600">● ${t("product.in_stock_n", { n: selectedVariant.stock })}</span> · ${esc(selectedVariant.name)}`
        : `<span style="color:var(--red);font-weight:600">● ${t("ui.sold_out")}</span> · ${esc(selectedVariant.name)}`) + cat;
    } else if (!variants.length) {
      stockLine.innerHTML = (product.in_stock
        ? `<span style="color:var(--green);font-weight:600">● ${t("product.in_stock_n", { n: product.stock })}</span>`
        : `<span style="color:var(--red);font-weight:600">● ${t("ui.sold_out")}</span>`) + cat;
    } else {
      stockLine.innerHTML = cat;
    }
  }

  function updateAvailabilityUI() {
    const ok = isAvailable();
    const maxQty = Math.max(1, Math.min(99, availableStock() || 99));
    qty = Math.max(1, Math.min(maxQty, qty));
    qtyVal.textContent = qty;
    addBtn.style.display = ok ? "" : "none";
    buyBtn.style.display = ok ? "" : "none";
    addBtn.disabled = !ok;
    buyBtn.disabled = !ok;
    notifyBtn.style.display = ok ? "none" : "";
    qtyBox.querySelectorAll("button").forEach((b) => (b.disabled = !ok));
  }

  function renderVariants() {
    if (!variants.length) return;
    variantsBox.innerHTML = variants.map((v) => {
      const sel = selectedVariant && v.id === selectedVariant.id;
      const opts = v.options && typeof v.options === "object"
        ? Object.entries(v.options).map(([k, val]) => `${esc(k)}: ${esc(val)}`).join(" · ")
        : "";
      return `<button class="chip ${sel ? "active" : ""}" data-id="${v.id}">
        ${esc(v.name)}${opts ? `<span class="chip-sub" style="display:block;font-size:11px;font-weight:500;opacity:.8">${opts}</span>` : ""}
        <span class="chip-stock" style="display:block;font-size:11px;font-weight:500;opacity:.8;${v.in_stock ? "" : "color:var(--red)"}">${v.in_stock ? t("ui.in_stock", { n: v.stock }) : t("ui.sold_out")}</span>
      </button>`;
    }).join("");
    variantsBox.querySelectorAll(".chip").forEach((c) => {
      c.addEventListener("click", () => {
        selectedVariant = variants.find((v) => v.id === Number(c.dataset.id));
        renderVariants();
        updatePricing();
        updateStock();
        updateAvailabilityUI();
      });
    });
  }

  qtyBox.addEventListener("click", (e) => {
    const step = Number(e.target.dataset.step);
    if (!step) return;
    qty = Math.max(1, Math.min(99, qty + step));
    qtyVal.textContent = qty;
    updatePricing();
  });

  renderVariants();
  updatePricing();
  updateStock();
  updateAvailabilityUI();

  if (images.length > 1) {
    const main = host.querySelector("#main img");
    host.querySelectorAll(".gthumb").forEach((t) => {
      t.addEventListener("click", () => {
        host.querySelectorAll(".gthumb").forEach((x) => x.classList.remove("active"));
        t.classList.add("active");
        if (main) main.src = images[Number(t.dataset.i)];
      });
    });
  }

  const add = async (thenGo) => {
    try {
      const cart = await api.post("/api/cart/add", { product_id: product.id, variant_id: selectedVariant ? selectedVariant.id : null, quantity: qty });
      applyCountBadge(cart.item_count);
      toast(t("ui.added_to_cart"), "success");
      if (thenGo) navigate("cart");
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const wishBtn = host.querySelector("#wish");
  wishBtn.addEventListener("click", async () => {
    try {
      if (wishlisted) {
        await api.del(`/api/wishlist/${product.id}`);
        wishlisted = false;
        toast(t("product.removed_from_wishlist"));
      } else {
        await api.post("/api/wishlist", { product_id: product.id });
        wishlisted = true;
        toast(t("product.added_to_wishlist"), "success");
      }
      wishBtn.classList.toggle("active", wishlisted);
      wishBtn.querySelector("svg").setAttribute("fill", wishlisted ? "currentColor" : "none");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  host.querySelector("#share").addEventListener("click", () => {
    shareToTelegram(t("product.share_text", { product: product.name, store: store.store_name }), productDeepLink(product.id, store));
  });

  host.querySelector("#scroll-reviews")?.addEventListener("click", () => {
    host.querySelector("#reviews-section").scrollIntoView({ behavior: "smooth" });
  });

  host.querySelector("#write-review").addEventListener("click", () => openReviewModal());

  host.querySelector("#add-cart").addEventListener("click", () => add(false));
  host.querySelector("#buy-now").addEventListener("click", () => add(true));

  host.querySelector("#notify").addEventListener("click", async () => {
    try {
      if (!subscribed) {
        await api.post(`/api/products/${product.id}/stock-alert`, { variant_id: selectedVariant ? selectedVariant.id : null });
        subscribed = true;
        notifyBtn.textContent = t("product.unsubscribe");
        toast(t("product.will_notify"), "success");
      } else {
        await api.del(`/api/products/${product.id}/stock-alert`);
        subscribed = false;
        notifyBtn.textContent = t("product.notify_me");
        toast(t("product.unsubscribed"));
      }
    } catch (err) {
      toast(err.message, "error");
    }
  });

  function openReviewModal() {
    const body = el(`
      <div>
        <p class="muted small" style="margin-bottom:8px">${t("product.tap_to_rate")}</p>
        <div class="rate-row" id="rate">
          ${[1, 2, 3, 4, 5].map((i) => `<button data-v="${i}" style="background:none;border:none;font-size:30px;color:var(--text-3);cursor:pointer">★</button>`).join("")}
        </div>
        <div class="field" style="margin-top:12px"><label>${t("product.your_review")}</label><textarea class="input" id="r-comment" placeholder="${t("product.how_was_it")}"></textarea></div>
      </div>`);
    let rating = 0;
    const stars = body.querySelectorAll("[data-v]");
    const paint = () => {
      stars.forEach((s) => {
        s.style.color = Number(s.dataset.v) <= rating ? "var(--star,#f6b73c)" : "var(--text-3)";
      });
    };
    stars.forEach((s) => s.addEventListener("click", () => { rating = Number(s.dataset.v); paint(); }));
    modal({
      title: t("product.write_review"),
      body,
      okText: t("ui.submit"),
      onOk: async () => {
        if (!rating) throw new Error(t("product.rate_error"));
        await api.post(`/api/products/${product.id}/reviews`, {
          rating,
          comment: body.querySelector("#r-comment").value.trim() || null,
        });
        toast(t("product.thanks_review"), "success");
        renderProduct(root, params);
      },
    });
  }

  root.innerHTML = "";
  root.appendChild(host);
}
