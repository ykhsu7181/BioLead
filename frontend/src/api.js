const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
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
    const message = body.error?.message || `Request failed: ${response.status}`;
    throw new Error(message);
  }
  return body.data;
}

export function getHealth() {
  return request("/api/health");
}

export function runPubMedSearch(payload) {
  return request("/api/pubmed/search", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function createResultPackage(payload) {
  return request("/api/result-packages", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getResultPackageDownloadUrl(packageId) {
  return `${API_BASE_URL}/api/result-packages/${encodeURIComponent(packageId)}/download`;
}

export function listLeads() {
  return request("/api/leads?page=1&page_size=50");
}

export function getLead(leadId) {
  return request(`/api/leads/${encodeURIComponent(leadId)}`);
}

export function getLeadServiceMatch(leadId) {
  return request(`/api/leads/${encodeURIComponent(leadId)}/service-match`);
}

export function listEmailDrafts() {
  return request("/api/email-drafts?page=1&page_size=50");
}

export function batchReviewEmailDrafts(payload) {
  return request("/api/email-drafts/batch-review", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function batchSendEmailDrafts(payload) {
  return request("/api/email-sends/batch-send", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listEmailSends() {
  return request("/api/email-sends?page=1&page_size=50");
}

export function createJob(payload) {
  return request("/api/jobs", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getJob(jobId) {
  return request(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function getJobItems(jobId) {
  return request(`/api/jobs/${encodeURIComponent(jobId)}/items?page=1&page_size=50`);
}
