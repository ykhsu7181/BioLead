import { request } from "./client";

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return query.toString();
}

export function getLeads(params = {}) {
  return request(`/api/leads?${buildQuery(params)}`);
}

export function getLeadFilterOptions() {
  return request("/api/leads/filter-options");
}

export function getTaskSummary(taskId) {
  return request(`/api/tasks/${encodeURIComponent(taskId)}/summary`);
}
