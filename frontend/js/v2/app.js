import { initTelegram, isTelegramAvailable, loginWithTelegram, loginDemo, logout, currentUser, isAdmin, refreshUser } from "./auth.js";
import { api, getStoredUser, getToken as apiGetToken } from "./api.js";
import { registerRoute, navigate, startRouter } from "./router.js";
import { toast, applyCountBadge } from "./ui.js";

// Buyer views
import { renderHome } from "./views/home.js";
import { renderProduct } from "./views/product.js";
import { renderCart } from "./views/cart.js";
import { renderCheckout } from "./views/checkout.js";
import { renderOrders } from "./views/orders.js";
import { renderOrder } from "./views/order.js";
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

function registerRoutes() {
  registerRoute("home", renderHome, { title: "Shop" });
  registerRoute("product/:id", renderProduct);
  registerRoute("cart", renderCart, { title: "Cart" });
  registerRoute("checkout", renderCheckout, { title: "Checkout" });
  registerRoute("orders", renderOrders, { title: "My orders" });
  registerRoute("order/:id", renderOrder);
  registerRoute("wishlist", renderWishlist, { title: "Wishlist" });
  registerRoute("profile", renderProfile, { title: "Profile" });
  registerRoute("login", renderLogin, { title: "Sign in" });

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

  registerRoutes();
  startRouter(document.getElementById("app"));
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
