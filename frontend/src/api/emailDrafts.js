import { request } from "./client";

export function generateBatchEmailDrafts(leadIds) {
  const uniqueLeadIds = [...new Set(leadIds)];
  return request("/api/email-drafts/batch-generate", {
    method: "POST",
    body: JSON.stringify({
      lead_ids: uniqueLeadIds,
      max_items: uniqueLeadIds.length
    })
  });
}
