export const EMAIL_STATUS = {
  verified: { label: "已验证", tone: "success" },
  missing: { label: "待补充", tone: "warning" },
  review_required: { label: "待确认", tone: "neutral" }
};

export const CONTACT_STATUS = {
  not_contacted: { label: "未联系", tone: "neutral" },
  pending_review: { label: "待审核", tone: "warning" },
  ready_to_send: { label: "待发送", tone: "primary" },
  sent: { label: "已发送", tone: "success" },
  rejected: { label: "已拒绝", tone: "danger" }
};

export function getLeadStatus(kind, value) {
  const mapping = kind === "email" ? EMAIL_STATUS : CONTACT_STATUS;
  return mapping[value] || { label: value || "未记录", tone: "neutral" };
}
