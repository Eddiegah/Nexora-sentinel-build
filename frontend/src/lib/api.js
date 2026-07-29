/**
 * Thin fetch wrapper that:
 *  - Attaches the JWT from localStorage on every request
 *  - Retries once on 502/503 (Render cold-start) with a 3-second delay
 *  - Redirects to /login on 401
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const COLD_START_STATUSES = new Set([502, 503, 504]);
const COLD_START_RETRY_DELAY_MS = 3000;

function getToken() {
  return localStorage.getItem("nexora_token");
}

async function request(path, options = {}, isRetry = false) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  } catch (networkError) {
    // Network-level failure (e.g. Render hasn't woken up yet)
    if (!isRetry) {
      await delay(COLD_START_RETRY_DELAY_MS);
      return request(path, options, true);
    }
    throw new Error("Network error — the server may be unavailable.");
  }

  if (COLD_START_STATUSES.has(response.status) && !isRetry) {
    await delay(COLD_START_RETRY_DELAY_MS);
    return request(path, options, true);
  }

  if (response.status === 401) {
    localStorage.removeItem("nexora_token");
    window.location.href = "/login";
    return;
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${response.status}`);
  }

  // 204 No Content
  if (response.status === 204) return null;
  return response.json();
}

function delay(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

// ── Public API ────────────────────────────────────────────────────────────────

export async function checkHealth() {
  return request("/health", { method: "GET" });
}

export async function login(email, password) {
  const data = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (data?.access_token) {
    localStorage.setItem("nexora_token", data.access_token);
  }
  return data;
}

export function logout() {
  localStorage.removeItem("nexora_token");
  window.location.href = "/login";
}

export function getRegions() {
  return request("/regions");
}

export function getRegion(regionId) {
  return request(`/regions/${regionId}`);
}

export function getLatestPrediction(regionId) {
  return request(`/regions/${regionId}/predictions/latest`);
}

export function getPredictionHistory(regionId) {
  return request(`/regions/${regionId}/predictions/history`);
}

export function triggerPrediction(regionId) {
  return request(`/regions/${regionId}/predict`, { method: "POST" });
}
