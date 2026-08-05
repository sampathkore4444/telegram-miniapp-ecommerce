import { api } from "../api.js";
import { navigate } from "../router.js";
import { el, esc, money, getStore, emptyState, toast, applyCountBadge } from "../ui.js";

export async function renderCart(root) {
  root.innerHTML = "";
  const store = await getStore();
  const cart = await api.get("/api/cart");

  if (cart.items.length === 0) {
    const empty = emptyState("&#128722;", "Your cart is empty", "Browse the shop and add items.");
    empty.appendChild(el(`<div class="center" style="padding-top:8px"><button class="btn btn-primary" style="width:auto;padding:12px 28px">Start shopping</button></div>`));
    empty.querySelector("button").addEventListener("click", () => navigate(""));
    const wrap = el(`<div class="container"></div>`);
    wrap.appendChild(empty);
    root.appendChild(wrap);
    return;
  }

  const freeThreshold = store.free_delivery_threshold;
  const deliveryFee = store.delivery_fee || 0;
  const freeEligible = freeThreshold != null && cart.subtotal >= freeThreshold;
  const estTotal = cart.subtotal + (freeEligible ? 0 : deliveryFee);
  const progress = freeThreshold != null ? Math.min(100, (cart.subtotal / freeThreshold) * 100) : 0;

  const host = el(`
    <div class="container sticky-page">
      <h1 class="title">Your cart</h1>

      ${freeThreshold != null
        ? `<div class="card" style="padding:12px 14px">
            <div class="progress-row">
              <span style="font-size:13px;font-weight:600" class="${freeEligible ? "" : "muted"}">
                ${freeEligible
                  ? `<span style="color:var(--green)">Free delivery unlocked!</span>`
                  : `Add <b style="color:var(--text)">${money(freeThreshold - cart.subtotal, store)}</b> more for free delivery`}
              </span>
              <span class="small muted" style="margin-left:auto">${Math.round(progress)}%</span>
            </div>
            <div class="progress"><div class="progress-fill" style="width:${progress}%"></div></div>
          </div>`
        : ""}

      <div id="items"></div>

      <div class="sticky-bar">
        <div class="sticky-inner">
          <div>
            <div class="small muted">Total</div>
            <div class="total-line" style="font-size:18px">${money(estTotal, store)}</div>
          </div>
          <button class="btn btn-primary grow" id="checkout">Proceed to checkout</button>
        </div>
      </div>
    </div>`);

  const itemsEl = host.querySelector("#items");
  const renderItems = async () => {
    itemsEl.innerHTML = "";
    for (const item of cart.items) {
      const p = item.product;
      const img = p.images && p.images.length ? `<img src="${esc(p.images[0])}" alt="" onerror="this.remove()">` : `<span style="font-size:26px">&#128230;</span>`;
      const row = el(`
        <div class="card" data-id="${item.id}" style="padding:12px">
          <div class="row">
            <div style="width:72px;height:72px;border-radius:12px;background:var(--bg-soft);overflow:hidden;display:flex;align-items:center;justify-content:center;flex-shrink:0">${img}</div>
            <div class="grow" style="min-width:0">
              <div style="font-weight:600;font-size:14px;line-height:1.3">${esc(p.name)}</div>
              ${item.variant ? `<div class="small" style="color:var(--accent);font-weight:600">${esc(item.variant.name)}</div>` : ""}
              <div class="small muted">${money(item.unit_price, store)} each</div>
              <div class="row" style="margin-top:10px">
                <div class="qty">
                  <button data-act="dec">−</button><span>${item.quantity}</span><button data-act="inc">+</button>
                </div>
                <div style="text-align:right">
                  <div style="font-weight:800;color:var(--text)">${money(item.unit_price * item.quantity, store)}</div>
                  <button class="btn btn-sm btn-outline" data-act="remove" style="margin-top:5px;color:var(--red)">Remove</button>
                </div>
              </div>
            </div>
          </div>
        </div>`);
      row.querySelectorAll("[data-act]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const act = btn.dataset.act;
          const qtyEl = row.querySelector(".qty span");
          let newQty = item.quantity;
          if (act === "inc") newQty = Math.min(99, item.quantity + 1);
          if (act === "dec") newQty = item.quantity - 1;
          if (act === "remove") newQty = 0;
          try {
            if (newQty <= 0) {
              await api.del(`/api/cart/${item.id}`);
            } else {
              await api.patch(`/api/cart/${item.id}`, { quantity: newQty });
              qtyEl.textContent = newQty;
              item.quantity = newQty;
            }
            renderCart(root);
          } catch (err) {
            toast(err.message, "error");
          }
        });
      });
      itemsEl.appendChild(row);
    }
  };

  host.querySelector("#checkout").addEventListener("click", () => navigate("checkout"));

  root.appendChild(host);
  await renderItems();
  const cart2 = await api.get("/api/cart");
  applyCountBadge(cart2.item_count);
}
