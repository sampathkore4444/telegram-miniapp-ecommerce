// Thin fetch wrapper with auth, JSON handling and normalized errors.
export const TOKEN_KEY = "tgshop_token";
export const USER_KEY = "tgshop_user";

export class ApiError extends Error {
  constructor(message, code, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setAuth(token, user) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function request(path, options = {}) {
  const { method = "GET", body, isForm = false, auth = true } = options;
  const headers = {};
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  if (body && !isForm) headers["Content-Type"] = "application/json";

  let resp;
  try {
    resp = await fetch(path, { method, headers, body: isForm ? body : body ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError("Network error. Please try again.", "network", 0);
  }

  if (resp.status === 401) {
    clearAuth();
    window.location.hash = "#/login";
    throw new ApiError("Session expired. Please sign in again.", "unauthorized", 401);
  }

  let data = null;
  const text = await resp.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = { message: text }; }
  }

  if (!resp.ok) {
    const message = data?.message || `Request failed (${resp.status})`;
    throw new ApiError(message, data?.code || "error", resp.status);
  }
  return data;
}

export async function downloadFile(path, filename) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(path, { headers });
  if (resp.status === 401) {
    clearAuth();
    window.location.hash = "#/login";
    throw new ApiError("Session expired. Please sign in again.", "unauthorized", 401);
  }
  if (!resp.ok) {
    const text = await resp.text();
    let data = null;
    try { data = JSON.parse(text); } catch { /* not json */ }
    throw new ApiError(data?.message || `Request failed (${resp.status})`, data?.code || "error", resp.status);
  }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || (path.split("/").pop() || "download");
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  get: (path, auth = true) => request(path, { auth }),
  post: (path, body) => request(path, { method: "POST", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  del: (path) => request(path, { method: "DELETE" }),
  upload: (path, formData) => request(path, { method: "POST", body: formData, isForm: true }),
  download: (path, filename) => downloadFile(path, filename),
};
