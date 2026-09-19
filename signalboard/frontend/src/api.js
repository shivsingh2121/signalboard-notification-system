export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "sb_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

function messageFrom(data, status) {
  if (!data) return `Request failed (${status}).`;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  if (data.error) return data.error;
  const first = Object.entries(data)[0];
  if (first) {
    const [, val] = first;
    return Array.isArray(val) ? String(val[0]) : String(val);
  }
  return `Request failed (${status}).`;
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Token ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      "Can't reach the server. If it's on Render's free plan it may be waking up — try again in 30 seconds.",
      0
    );
  }
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    if (res.status === 401 && token) tokenStore.clear();
    throw new ApiError(messageFrom(data, res.status), res.status, data);
  }
  return data;
}

// Field-level errors from DRF: { field: ["msg"] } -> { field: "msg" }
export function fieldErrors(err) {
  const out = {};
  if (err?.data && typeof err.data === "object") {
    for (const [k, v] of Object.entries(err.data)) out[k] = Array.isArray(v) ? String(v[0]) : String(v);
  }
  return out;
}
