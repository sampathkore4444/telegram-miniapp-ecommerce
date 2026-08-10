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
    // Use the app's designed palette (light/dark CSS variables) rather than
    // adopting the user's Telegram theme colors, for a consistent brand look.
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
