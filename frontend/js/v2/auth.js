// Telegram WebApp bootstrap + login/session helpers.
import { api, setAuth, clearAuth, getStoredUser, getToken as apiGetToken } from "./api.js";

let tg = null;
try {
  if (window.Telegram?.WebApp) tg = window.Telegram.WebApp;
} catch { /* non-Telegram browser */ }

export const telegram = tg;

export function isTelegramAvailable() {
  return Boolean(tg && tg.initData);
}

export function initTelegram() {
  if (!tg) return;
  try {
    tg.ready();
    tg.expand();
    document.documentElement.dataset.scheme = tg.colorScheme || "light";
    const h = tg.themeParams;
    if (h?.bg_color) document.documentElement.style.setProperty("--bg", h.bg_color);
    if (h?.text_color) document.documentElement.style.setProperty("--text", h.text_color);
    if (h?.hint_color) document.documentElement.style.setProperty("--text-2", h.hint_color);
    if (h?.button_color) document.documentElement.style.setProperty("--accent", h.button_color);
    if (h?.secondary_bg_color) document.documentElement.style.setProperty("--bg-soft", h.secondary_bg_color);
  } catch { /* noop */ }
}

export async function loginWithTelegram() {
  const initData = tg?.initData;
  if (!initData) throw new Error("Telegram session not available");
  const data = await api.post("/api/auth/telegram", { init_data: initData });
  setAuth(data.token, data.user);
  return data.user;
}

export async function loginDemo(role = "buyer") {
  const data = await api.post(`/api/auth/demo?role=${role}`, {});
  setAuth(data.token, data.user);
  return data.user;
}

export function currentUser() {
  return getStoredUser();
}

export function isAdmin() {
  return currentUser()?.role === "admin";
}

export function logout() {
  clearAuth();
  window.location.hash = "#/login";
}

export async function refreshUser() {
  try {
    const user = await api.get("/api/me");
    setAuth(null, user);
    return user;
  } catch {
    return currentUser();
  }
}
