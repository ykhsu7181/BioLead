const TASK_STATUS = Object.freeze({
  success: { label: "已完成", tone: "primary" },
  completed: { label: "已完成", tone: "primary" },
  running: { label: "处理中", tone: "primary" },
  pending: { label: "等待处理", tone: "neutral" },
  failed: { label: "失败", tone: "danger" },
  cancelled: { label: "已取消", tone: "neutral" },
  blocked: { label: "已阻止", tone: "warning" }
});

export function getTaskStatus(status) {
  return TASK_STATUS[String(status || "").toLowerCase()] || {
    label: "未知状态",
    tone: "neutral"
  };
}
