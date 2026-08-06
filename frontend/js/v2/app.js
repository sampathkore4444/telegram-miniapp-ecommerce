import { initTelegram, isTelegramAvailable, loginWithTelegram, loginDemo, logout, currentUser, isAdmin, refreshUser } from "./auth.js";
import { api, getStoredUser, getToken as apiGetToken } from "./api.js";
import { registerRoute, navigate, startRouter } from "./router.js";
import { toast, applyCountBadge } from "./ui.js";
import { t, getLang, LANG_META } from "./i18n.js";

// Buyer views
import { renderHome } from "./views/home.js";
import { renderProduct } from "./views/product.js";
import { renderCart } from "./views/cart.js";
import { renderCheckout } from "./views/checkout.js";
import { renderOrders } from "./views/orders.js";
import { renderOrder } from "./views/order.js";
import { renderPayment } from "./views/payment.js";
import { renderProfile } from "./views/profile.js";
import { renderLogin } from "./views/login.js";
import { renderWishlist } from "./views/wishlist.js";
// Admin views
import { renderDashboard } from "./views/admin/dashboard.js";
import { renderProducts } from "./views/admin/products.js";
import { renderProductEditor } from "./views/admin/productEditor.js";
import { renderCategories } from "./views/admin/categories.js";
import { renderAdminOrders } from "./views/admin/orders.js";
import { renderAdminOrderDetail } from "./views/admin/orderDetail.js";
import { renderSettings } from "./views/admin/settings.js";
import { renderCoupons } from "./views/admin/coupons.js";
import { renderReviews } from "./views/admin/reviews.js";
import { renderCustomers, renderCustomerDetail } from "./views/admin/customers.js";
import { renderBroadcasts } from "./views/admin/broadcasts.js";

function registerRoutes() {
  registerRoute("home", renderHome, { titleKey: "titles.shop" });
  registerRoute("product/:id", renderProduct);
  registerRoute("cart", renderCart, { titleKey: "nav.cart" });
  registerRoute("checkout", renderCheckout, { titleKey: "checkout.title" });
  registerRoute("orders", renderOrders, { titleKey: "orders.title" });
  registerRoute("order/:id", renderOrder);
  registerRoute("pay/order/:id", renderPayment);
  registerRoute("wishlist", renderWishlist, { titleKey: "wishlist.title" });
  registerRoute("profile", renderProfile, { titleKey: "nav.profile" });
  registerRoute("login", renderLogin, { titleKey: "titles.sign_in" });

  registerRoute("admin", renderDashboard, { title: "Admin" });
  registerRoute("admin/products", renderProducts, { title: "Products" });
  registerRoute("admin/product/new", renderProductEditor, { title: "New product" });
  registerRoute("admin/product/:id", renderProductEditor);
  registerRoute("admin/categories", renderCategories, { title: "Categories" });
  registerRoute("admin/orders", renderAdminOrders, { title: "Orders" });
  registerRoute("admin/order/:id", renderAdminOrderDetail);
  registerRoute("admin/settings", renderSettings, { title: "Settings" });
  registerRoute("admin/coupons", renderCoupons, { title: "Coupons" });
  registerRoute("admin/reviews", renderReviews, { title: "Reviews" });
  registerRoute("admin/customers", renderCustomers, { title: "Customers" });
  registerRoute("admin/customer/:id", renderCustomerDetail);
  registerRoute("admin/broadcasts", renderBroadcasts, { title: "Broadcasts" });
  registerRoute("notfound", async (root) => {
    root.innerHTML = `<div class="empty"><span class="ico">&#129300;</span>Page not found</div>`;
  });
}

function bindNav() {
  const map = { home: "", cart: "cart", orders: "orders", profile: "profile", admin: "admin" };
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => navigate(map[btn.dataset.nav]));
  });
}

function updateNavLabels() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
}

function applyLangUI() {
  document.documentElement.lang = LANG_META[getLang()].locale.split("-")[0];
  updateNavLabels();
}

async function boot() {
  initTelegram();
  bindNav();

  const nav = document.getElementById("nav-bar");
  nav.classList.remove("hidden");
  nav.classList.add("hidden"); // keep hidden until authed

  if (!getStoredUser()) {
    if (!isTelegramAvailable()) {
      window.location.hash = "#/login";
    } else {
      try {
        await loginWithTelegram();
      } catch (err) {
        console.warn("tg login failed", err);
        window.location.hash = "#/login";
      }
    }
  }

  // Refresh user from server (validates token, refreshes role) when we have a token
  if (getStoredUser() && apiGetToken()) {
    try {
      await refreshUser();
    } catch { /* token expired -> api handles redirect */ }
  }

  const applyNav = () => {
    const user = currentUser();
    const authed = Boolean(user);
    nav.classList.toggle("hidden", !authed);
    document.querySelector(".admin-nav")?.classList.toggle("hidden", !isAdmin());
    if (!authed && !["login"].includes(window.location.hash.replace(/^#\/?/, ""))) {
      window.location.hash = "#/login";
    }
  };

  window.addEventListener("hashchange", () => {
    applyNav();
    updateCartBadge();
  });

  window.addEventListener("langchange", () => {
    applyLangUI();
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });

  registerRoutes();
  startRouter(document.getElementById("app"));
  applyLangUI();
  applyNav();
  updateCartBadge();
}

async function updateCartBadge() {
  try {
    const cart = await api.get("/api/cart");
    applyCountBadge(cart.item_count);
  } catch { /* ignore */ }
}

boot();
