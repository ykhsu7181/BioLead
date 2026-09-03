const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });
  const body = await response.json().catch(() => ({
    success: false,
    data: null,
    error: { code: "INVALID_JSON", message: "Response was not JSON." }
  }));
  if (!response.ok || body.success === false) {
    throw new Error(body.error?.message || `Request failed: ${response.status}`);
  }
  return body.data;
}
