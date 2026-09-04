import { getApiUrl, request } from "./client";

export function createTaskResultPackage(taskId) {
  return request("/api/result-packages", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId })
  });
}

export function downloadResultPackage(packageId) {
  const link = document.createElement("a");
  link.href = getApiUrl(`/api/result-packages/${encodeURIComponent(packageId)}/download`);
  link.download = "scholarlead_results.xlsx";
  document.body.appendChild(link);
  link.click();
  link.remove();
}
