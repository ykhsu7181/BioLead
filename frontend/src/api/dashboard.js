import { request } from "./client";

export function getDashboardSummary() {
  return request("/api/dashboard/summary");
}
